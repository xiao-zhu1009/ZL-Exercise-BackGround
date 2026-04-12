# models/__init__.py
# 统一导入所有模型，确保 Base.metadata 能感知到所有表
# main.py 只需 import models 即可触发所有模型注册

from models.user import User
from models.action import Action
from models.diet import DietArticle, Food, DietRecord
from models.course import Course, Reservation
from models.training import BodyRecord, WorkoutRecord, TrainingPlan, CoachStudent
from models.body_stats import UserBodyStats
from models.coach_application import CoachApplication
