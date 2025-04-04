from enum import Enum

class TaskType(str, Enum):
    DATA_COLLECTION = "data_collection"
    CONTENT_ANALYSIS = "content_analysis"
    GENERATE_REPORT = "generate_report"
    # Placeholder for other potential MVP task types
    PROCESS_ITEM = "process_item" # Example task type for demonstration
    CHAINED_TASK = "chained_task" # Example task type for workflow demo 