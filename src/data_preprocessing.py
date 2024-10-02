import pandas as pd

def merge_data(df_registration, df_courses):
    try:
        df_merged = pd.merge(df_registration, df_courses, left_on='G CODE', right_on='Course code', how='left')
        df_merged['Professor'] = df_merged['Faculty Name']
        df_merged = df_merged[['Roll No.', 'G CODE', 'Professor']]
        return df_merged.dropna()
    except Exception as e:
        print(f"Error occurred while merging data: {e}")
        raise e 

def prepare_student_course_map(df):
    try:
        return {roll: list(group['G CODE']) for roll, group in df.groupby('Roll No.')}
    except Exception as e:
        print(f"Error occurred while preparing student course map: {e}")
        raise e  
def create_course_professor_map(df):
    try:
        return pd.Series(df['Professor'].values, index=df['G CODE']).to_dict()
    except Exception as e:
        print(f"Error occurred while creating course professor map: {e}")
        raise e 
