from sqlmodel import Field, Relationship, SQLModel, create_engine, Session, select
from sqlalchemy import Column
from sqlalchemy.types import JSON
from typing import Dict, Any, Optional
import io
from data.data import get_task_by_id

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
                select(Run.correct)
                .where(Run.graph_id == self.id)
            ).all()
            return 1.0 if not runs else sum(runs) / len(runs)


    def run(self, task_id):
        # Create a new namespace for each execution
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
        try:
            exec(self.graph, namespace)
            graph_class = namespace.get("Agent")
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
            
            with Session(_engine) as session:
                run = Run(
                    graph_id=self.id,
                    task_id=task_id,
                    log=log_data,
                    final_output=ret,
                    score=1 - abs(ret - task['answer']) / task['answer']
                )
                session.add(run)
                session.commit()


        except ModuleNotFoundError as e:
            print(f"ModuleNotFoundError: {e}")
            raise
        except Exception:
            print("--- Error with graph code ---")
            print(self.graph)
            print("--- error ---")
            raise
        

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


def get_graph_from_a_file(path: str):
    with open(path, "r") as f:
        graph = f.read()
    graph = Graph(graph=graph)
    with Session(_engine) as session:
        session.add(graph)
        session.commit()
        session.refresh(graph)
    return graph

if __name__ == '__main__':
    graph = get_graph_from_a_file('pretty.py')
    graph.run('37_2')
