from sqlmodel import Field, Relationship, SQLModel, create_engine, Session, select
from sqlalchemy import Column, func
from sqlalchemy.types import JSON
from typing import Dict, Any, Optional
import io
import hashlib
import os
import sys
import functools
from string import Formatter
from PIL import Image
import itertools
import re
from data.data import get_task_by_id, get_all_task_ids
from pydantic import BaseModel
import datetime

import openai
from stocholm_prompt import WORKFLOW_OPTIMIZE_PROMPT, WORKFLOW_INPUT, OPERATOR_DESCRIPTION
from ugly import compute_probabilities, format_experience, format_log, xml_extract

db_name = "data/db.sqlite"

class Graph(SQLModel, table=True):
    id: int = Field(primary_key=True)
    graph: str
    father_id: Optional[int] = Field(default=None, foreign_key="graph.id")
    change: Optional[str] = Field(default=None)
    runs: list["Run"] = Relationship(back_populates="graph")

    @property
    def father(self):
        return Graph.get(self.father_id)
    @father.setter
    def father(self, value):
        self.father_id = value.id
    @property
    def children(self):
        with Session(_engine) as session:
            return session.exec(
                select(Graph)
                .where(Graph.father_id == self.id)
            ).all()

    @property
    def score(self) -> float:
        with Session(_engine) as session:
            runs = session.exec(
                select(Run.score)
                .where(Run.graph_id == self.id)
            ).all()
            return 1.0 if not runs else sum(runs) / len(runs)


    def run(self, task_id):
        namespace = {
            '__name__': '__exec__',
            '__package__': None,
            'SQLModel': SQLModel,
            'Field': Field,
            'Relationship': Relationship,
            'Column': Column,
            'JSON': JSON,
            'Optional': Optional,
            'Dict': Dict,
            'Any': Any
        }
        task = get_task_by_id(task_id)
        image = task['image']
        question = task['question']
        log_output = None
        try:
            exec(self.graph, namespace)
            with open('ngkx.py', 'r') as f:
                exec(f.read(), namespace)
            graph_class = namespace.get("LoggingAgent")
            graph = graph_class(image)
            import sys
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = sys.stderr = log_output = io.StringIO()
            ret = graph(question)
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            log_data = {
                'log': log_output.getvalue(),
                'final_answer': ret
            }
            print(log_data)

            match = re.search(r'{(.*?)}', ret)
            answer = match.group(1) if match else ret
            
            with Session(_engine) as session:
                run = Run(
                    graph_id=self.id,
                    task_id=task_id,
                    log=log_data,
                    final_output=ret,
                    score=(answer == task['answer']) or max(0, 0.5 - abs(float(answer) - float(task['answer'])) / (float(task['answer']) + 0.01))
                )
                session.add(run)
                session.commit()


        except ModuleNotFoundError as e:
            print(f"ModuleNotFoundError: {e}")
            return 'ERROR'
        except Exception:
            print("--- Error running graph ---")
            if log_output:
                print(log_output.getvalue())
            print("--- error ---")
            return 'ERROR'


class Run(SQLModel, table=True):
    graph_id: int = Field(primary_key=True, foreign_key="graph.id")
    task_id: str = Field(primary_key=True)
    log: Dict[str, Any] = Field(sa_column=Column(JSON))
    final_output: str | None = Field(default=None)
    score: float
    graph: Graph = Relationship(back_populates="runs")

    @property
    def task(self):
        return get_task_by_id(self.task_id)

_engine = create_engine(f"sqlite:///{db_name}")
SQLModel.metadata.create_all(_engine)


def put(x):
    with Session(_engine) as session:
        session.add(x)
        session.commit()
        return x

def get_graph_from_a_file(path: str):
    with open(path, "r") as f:
        graph = f.read()
    graph = Graph(graph=graph)
    with Session(_engine) as session:
        session.add(graph)
        session.commit()
        session.refresh(graph)
    return graph

# if __name__ == '__main__':
#     graph = get_graph_from_a_file('pretty.py')
#     graph.run('37_2')
#     exit(0)


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
            .order_by(func.avg(Run.score).desc())
            .limit(remaining)
        )
        graphs_with_runs = session.exec(stmt_with_runs).all()
        return graphs_with_zero_runs + graphs_with_runs


def get_high_variation_task(k=1):
    ret = []
    with Session(_engine) as session:
        run_task_ids = session.exec(select(Run.task_id)).all()
        for task_id in get_all_task_ids():
            if task_id not in run_task_ids:
                ret.append(task_id)
    if len(ret) >= k:
        return ret[:k]
    with Session(_engine) as session:
        ret.extend(session.exec(select(Run.task_id).group_by(Run.task_id).order_by(func.std(Run.score).desc()).limit(k - len(ret))).all())
    return ret[0] if k == 1 else ret


def db_session(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with Session(_engine) as session:
            return func(*args, **kwargs)
    return wrapper


@db_session
def optimize(run: Run):
    print('A')
    graph = run.graph
    print(graph.id)
    response = openai.chat.completions.create(
        model = 'gemini-2.0-flash',
        messages=[
            {'role': 'user', 'content': WORKFLOW_OPTIMIZE_PROMPT.format(
                experience=WORKFLOW_INPUT.format(
                    experience=format_experience(graph),
                    score=graph.score,
                    agent=graph.graph,
                    log=format_log(run.log)
                ),
            )}
        ]
    )
    print(format_log(response))
    class Opti(BaseModel):
        modification: str = Field(..., description='summarize the modification you plan to make')
        agent: str = Field(..., description='the modified agent.py')
    ret = xml_extract(response.choices[0].message.content, Opti)
    graph = Graph(graph=ret.agent, father=graph, change=ret.modification)
    graph = put(graph)
    with open(f"{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_graph_{graph.id}.py", "w") as f:
        f.write(graph.graph)

    task = get_high_variation_task()
    result, run = graph.run(task)





if __name__ == '__main__':
    with Session(_engine) as session:
        run = session.exec(select(Run).order_by(Run.score.desc())).first()
        optimize(run)
    exit(0)


