# Time Table Optimization: Core Functionality

## Introduction
This branch, `core-functionality`, houses the essential modules required for the Time Table Optimization project. Each module is designed to perform specific tasks. 

## Modules Description

### `data_preprocessing.py`
- **Purpose**: Handles the preprocessing of raw data from the data files.
- **Functionality**: Converts the data into usable data structures, cleans data, and prepares it for the scheduling model.
- **Input**: Takes data files from the `data/` directory.
- **Output**: Outputs cleaned and structured data. 

### `schedule_model.py`
- **Purpose**: Contains the core scheduling logic using Google's OR-Tools library. 
- **Functionality**: Implements constraint-based scheduling to ensure no overlapping classes and optimizes time slot preference of the professors.
- **Input**: Processed data from `data_preprocessing.py`.
- **Output**: Generates a timetable that respects all input constraints and optimizes resource usage.

### `conflict_checker.py`
- **Purpose**: Ensures that the generated timetable has no conflicts.
- **Functionality**: Validates the output of `schedule_model.py` by checking for any overlapping schedules among courses, students, or teachers.
- **Input**: Timetable data from `schedule_model.py`.
- **Output**: Confirms the validity of the timetable or reports conflicts.

### `utilities.py`
- **Purpose**: Provides auxiliary functions that support data handling and manipulation across other modules.
- **Functionality**: Includes functions for date and time manipulation, data conversion, and other common utilities needed by various parts of the project.

### `main.py`
- **Purpose**: Acts as the central executable for the application, tying all other modules together.
- **Functionality**: Orchestrates the flow of data through the system, from preprocessing to scheduling and conflict checking.
- **Usage**: Run this script to execute the entire timetable generation process.
