import pandas as pd

# Load the CSV data into a DataFrame
df = pd.read_csv("faculty_pref1.csv")  # Replace "your_csv_file.csv" with the actual path to your CSV file

# Create a dictionary to map abbreviated week names to full names
week_mapping = {
    "Mon": "Monday",
    "Tue": "Tuesday",
    "Wed": "Wednesday",
    "Thu": "Thursday",
    "Fri": "Friday"
}

# Create a new DataFrame to store the results
result_df = pd.DataFrame(columns=["Faculty Name", "Busy Slot"])

# Iterate through each row in the original DataFrame
for index, row in df.iterrows():
    faculty_name = row["Faculty Name"]
    for col in df.columns[1:]:  # Skip the first column (Faculty Name)
        day, time = col.split()
        if row[col]:  # If the slot is busy
            busy_slot = f"{week_mapping[day]} {time}"
            new_row = pd.DataFrame({"Faculty Name": [faculty_name], "Busy Slot": [busy_slot]})
            result_df = pd.concat([result_df, new_row], ignore_index=True)

# Print or save the result DataFrame
print(result_df)
result_df.to_csv("faculty_pref2.csv", index=False)  # Save the result to a CSV file