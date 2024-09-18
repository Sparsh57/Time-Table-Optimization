import pandas as pd

import pandas as pd

def load_data():
    path_prefix = './data/'  # Adjust this if your directory structure is different
    df_registration = pd.read_csv(path_prefix + 'Student Registration Data.csv')
    df_courses = pd.read_csv(path_prefix + 'Students - Courses Offere List - AY 2024-25 - Term 1 - Sheet1.csv')
    df_faculty_pref = pd.read_csv(path_prefix + 'faculty_pref.csv')
    return df_registration, df_courses, df_faculty_pref


def merge_data(df_registration, df_courses):
    df_merged = pd.merge(df_registration, df_courses, left_on='G CODE', right_on='Course code', how='left')
    df_merged['Professor'] = df_merged['Faculty Name']
    df_merged = df_merged[['Roll No.', 'TRIM', 'SECTION', 'G CODE', 'Sections', 'Professor']]
    return df_merged.dropna()

def prepare_student_course_map(df):
    return {roll: list(group['G CODE']) for roll, group in df.groupby('Roll No.')}

def create_course_professor_map(df):
    return pd.Series(df['Professor'].values, index=df['G CODE']).to_dict()
