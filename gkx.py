from sqlmodel import Field, Relationship, SQLModel, create_engine, Session, select
from sqlalchemy import Column, func
from sqlalchemy.types import JSON
from typing import Dict, Any, Optional
import hashlib
import os
import sys
import functools
from string import Formatter
from action_node import operators
from PIL import Image
import itertools

db_name = "runs.db"

class TupleFormatter(Formatter):
    def format(self, format_string, *args, **kwargs):
        if all(isinstance(x, str) for x in itertools.chain(args, kwargs.values())):
            return super().format(format_string, *args, **kwargs)   
        result = []
        for literal_text, field_name, format_spec, conversion in self.parse(format_string):
            if literal_text:
                result.append(literal_text)
            if field_name is not None:
                value, _ = self.get_field(field_name, args, kwargs)
                if isinstance(value, Image.Image):
                    result.append(value)
                else:
                    formatted = self.format_field(value, format_spec)
                    result.append(formatted)
        return tuple(result)

class MyStr(str):
    def format(self, *args, **kwargs):
        formatter = TupleFormatter()
        return formatter.format(self, *args, **kwargs)


class Graph(SQLModel, table=True):
    id: int = Field(primary_key=True)
    graph: str
    prompt: str
    father_id: Optional[int] = Field(default=None)
    children_id: list[int] = Field(default=[], sa_column=Column(JSON))
    change: Optional[str] = Field(default=None)
    runs: list["Run"] = Relationship(back_populates="graph")

    @property
    def score(self) -> float:
        with Session(_engine) as session:
            # Get all runs for this graph
            runs = session.exec(
                select(Run.correct).where(Run.graph_id == self.id)
            ).all()
            
            if not runs:
                return 1.0
            
            # Calculate the ratio of correct runs
            return sum(1 for run in runs if run) / len(runs)

    @classmethod
    def from_folder(cls, foldername):
        with open(os.path.join(foldername, "graph.py"), "r") as f:
            graph = f.read()
        with open(os.path.join(foldername, "prompt.py"), "r") as f:
            prompt = f.read()
        return cls(graph=graph, prompt=prompt)

    @property
    def father(self):
        if not self.father_id:
            return None
        with Session(_engine) as session:
            return session.get(Graph, self.father_id)
    
    @property
    def children(self):
        with Session(_engine) as session:
            return [session.get(Graph, id) for id in self.children_id]

    def run(self):
        graph_code = self.graph + '\n' + self.prompt
        namespace = {'__name__': '__exec__', '__package__': None}
        
        try:
            exec(graph_code, namespace)
            graph_class = namespace.get("Graph")
            namespace = {
                k: (MyStr(v) if isinstance(v, str) else v) for k, v in namespace.items()
            }
            graph = graph_class(operators=operators, prompts=namespace)
        except ModuleNotFoundError as e:
            print(f"ModuleNotFoundError: {e}")
            raise
        except Exception:
            print("--- Error reading graph code ---")
            print(graph_code)
            print("--- error ---")
            raise

        def extract_local_variables_wrapper(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                original = sys.gettrace()
                captured_locals = {}
                def trace(frame, event, _arg):
                    if event == 'return' and frame.f_code is func.__code__:
                        nonlocal captured_locals
                        captured_locals = frame.f_locals
                    return trace
                sys.settrace(trace)
                try:
                    result = await func(*args, **kwargs)
                except:
                    sys.settrace(original)
                    raise
                sys.settrace(original)
                captured_locals = dict(captured_locals)
                captured_locals.pop('self')
                return result, captured_locals
            return wrapper
        
        def log_to_db_wrapper(graph_id): 
            def decorator(func):
                @functools.wraps(func)
                async def wrapper(task):
                    # Check if this graph has already run this task
                    with Session(_engine) as session:
                        existing_run = session.exec(
                            select(Run).where(
                                Run.graph_id == graph_id,
                                Run.task_id == task['question_id']
                            )
                        ).first()
                        if existing_run:
                            return existing_run.final_output, existing_run.correct

                    result, captured_locals = await func((task['image'], task['question']))
                    correct = (result == task['question_answer'])

                    def patch_keep_only_str(d: dict):
                        return {k: v for k, v in d.items() if isinstance(v, str)}
                    
                    run = Run(
                        graph_id=graph_id,
                        task_id=task['question_id'],
                        log=patch_keep_only_str(captured_locals),
                        final_output=result,
                        correct=correct
                    )

                    assert isinstance(run, Run)
                    assert isinstance(run.graph_id, int)
                    assert isinstance(run.task_id, str)
                    assert isinstance(run.log, dict)
                    assert all(isinstance(k, str) and isinstance(v, str) for k, v in run.log.items())
                    assert isinstance(run.final_output, str), run.final_output
                    assert isinstance(run.correct, bool), run.correct
                    
                    with Session(_engine) as session:
                        session.add(run)
                        session.commit()
                    
                    return result, correct
                return wrapper
            return decorator
        
        return log_to_db_wrapper(self.id)(extract_local_variables_wrapper(graph.run))
    
class Run(SQLModel, table=True):
    graph_id: int = Field(primary_key=True, foreign_key="graph.id")
    task_id: str = Field(primary_key=True)
    log: Dict[str, Any] = Field(sa_column=Column(JSON))
    final_output: str | None = Field(default=None)
    correct: bool
    graph: Graph = Relationship(back_populates="runs")

    @property
    def task(self):
        from zero import get_task_data
        return get_task_data(self.task_id)

_engine = create_engine(f"sqlite:///{db_name}")
SQLModel.metadata.create_all(_engine)
c
import polars as pl

df = pl.read_parquet('/home/jkp/Téléchargements/zerobench_subquestions-00000-of-00001.parquet')
tasks = df['question_id'].to_list()

def get_high_variation_task(k=1):
    ret = []
    with Session(_engine) as session:
        run_task_ids = session.exec(select(Run.task_id)).all()
        for task_id in tasks:
            if task_id not in run_task_ids:
                ret.append(task_id)
    if len(ret) >= k:
        return ret[:k]
    with Session(_engine) as session:
        ret.extend(session.exec(select(Run.task_id).group_by(Run.task_id).order_by(func.std(Run.correct).desc()).limit(k - len(ret))).all())
    return ret

def put(x):
    with Session(_engine) as session:
        session.add(x)
        session.commit()
        return x

def get_graph_from_a_folder(folder: str):
    with open(os.path.join(folder, "graph.py"), "r") as f:
        graph = f.read()
    with open(os.path.join(folder, "prompt.py"), "r") as f:
        prompt = f.read()
    graph = Graph(graph=graph, prompt=prompt)
    return put(graph)

if __name__ == '__main__':
    get_graph_from_a_folder('sample/crop')
    get_graph_from_a_folder('sample/cot')

def test_get_graph_from_a_folder():
    with Session(_engine) as session:
        print(len(session.exec(select(Graph)).all()))
    get_graph_from_a_folder("sample/cot")
    with Session(_engine) as session:
        print(len(session.exec(select(Graph)).all()))

def get_strongest_graph(k: int):
    with Session(_engine) as session:
        stmt_zero_runs = select(Graph).where(~Graph.runs.any()).limit(k)
        graphs_with_zero_runs = session.exec(stmt_zero_runs).all()
        if len(graphs_with_zero_runs) >= k:
            return graphs_with_zero_runs[:k]
        remaining = k - len(graphs_with_zero_runs)
        stmt_with_runs = (
            select(Graph)
            .join(Run)
            .group_by(Graph.id)
            .order_by(func.avg(Run.correct).desc())
            .limit(remaining)
        )
        graphs_with_runs = session.exec(stmt_with_runs).all()
        return graphs_with_zero_runs + graphs_with_runs

def get_hardest_task(k=1):
    with Session(_engine) as session:
        return session.exec(
            select(Run.task_id)
            .group_by(Run.task_id)
            .order_by(func.avg(Run.correct).asc())
            .limit(k)
        ).all()
    
def test_get_strongest_graph():
    assert isinstance(get_strongest_graph(), Graph)
def test_get_hardest_task():
    ret = get_hardest_task(2)
    assert isinstance(ret, list)
    assert len(ret) == 2
    assert isinstance(ret[0], str)