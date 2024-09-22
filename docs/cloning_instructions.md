# Time Table Optimization

This project is designed to automate the scheduling of classes by taking pre-existing data, loading it into a database, retrieving relevant data for processing, and then applying an optimization algorithm to generate an optimal timetable.

## Getting Started

To run the project on your computer, follow these steps. Please note that the data has already been populated in the database, so there is no need to run the data loading scripts.

### Prerequisites

- Python 3.8 or higher
- MySQL Server (Credentials and access provided separately)
- Necessary Python libraries which can be installed using `requirements.txt` provided in the repository.

### Cloning the Repository

First, clone the repository to your local machine using Git:

```bash
git clone https://github.com/Sparsh57/Time-Table-Optimization.git -b feature/core-functionality
cd Time-Table-Optimization
```

### Setting Up the Environment

It's recommended to create a virtual environment to manage dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

### Running the Algorithm

To run the scheduling algorithm, follow these steps:

1. **Data Retrieval**: The script connects to a MySQL database to fetch required data for the model. This data includes course details, professor assignments, and their available time slots.

    Navigate to the `src` directory:

    ```bash
    cd src
    ```

    Run the data retrieval script:

    ```bash
    python database_management/database_retrieval.py
    ```

    This will fetch data and prepare it for the scheduling algorithm, storing intermediate results in the `data` directory.

2. **Schedule Optimization**: The main script processes the retrieved data using a scheduling algorithm that optimizes the timetable based on available slots and course requirements.

    Run the main script to execute the scheduling algorithm:

    ```bash
    python main.py
    ```

    The output will be displayed on the console and, depending on your setup, might also be saved to a file or database.

3. **FastAPI**: The main_backend.py file is a FastAPI file in which we have endpoints to insert time_slots and extract time_slots.

   Run the main_backend script to execute the API:
   ```bash
    fastapi dev main_backend.py
    ```

### Output
The final schedule will be output to the console, showing which courses are scheduled at what times, trying to minimize conflicts. 
