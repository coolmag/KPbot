from pydantic import BaseModel, Field
from typing import List


class BudgetItem(BaseModel):
    item: str = Field(..., description="Название позиции")
    price: str = Field(..., description="Стоимость")
    time: str = Field(..., description="Срок выполнения")


class SolutionStep(BaseModel):
    step_name: str
    description: str


class Plan(BaseModel):
    name: str
    description: str
    budget_items: List[BudgetItem]


class Proposal(BaseModel):
    title: str
    executive_summary: str
    client_pain_points: List[str]
    solution_steps: List[SolutionStep]
    plans: List[Plan]
    why_us: str
    cta: str
