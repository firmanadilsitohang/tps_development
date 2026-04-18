from flask_sqlalchemy import SQLAlchemy

# 1. Definisikan db di sini
db = SQLAlchemy()

# 2. Import model-modelnya SETELAH db didefinisikan
from .user import User
from .employee import Employee, Plant, Division, Department, BatchStat, WorkshopEvaluation
from .module import LearningModule
from .development import Training, Activity