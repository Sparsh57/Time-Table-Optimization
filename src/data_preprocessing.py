import pandas as pd

def merge_data(df_registration, df_courses):
    df_merged = pd.merge(df_registration, df_courses, left_on='G CODE', right_on='Course code', how='left')
    df_merged['Professor'] = df_merged['Faculty Name']
    df_merged = df_merged[['Roll No.','G CODE', 'Professor']]
    return df_merged.dropna()

def prepare_student_course_map(df):
    return {roll: list(group['G CODE']) for roll, group in df.groupby('Roll No.')}

def create_course_professor_map(df):
    """
    Create a mapping from course to professor.
    If multiple professors are assigned to a course (ampersand-separated), 
    takes the first professor for backward compatibility with existing algorithm.
    
    :param df: DataFrame with 'G CODE' and 'Professor' columns
    :return: Dictionary mapping course codes to professor emails
    """
    course_prof_map = {}
    
    for index, row in df.iterrows():
        course_code = row['G CODE']
        professor_str = row['Professor']
        
        # Handle ampersand-separated professors by taking the first one
        if pd.isna(professor_str):
            continue
            
        professors = [prof.strip() for prof in str(professor_str).split('&')]
        if professors and professors[0]:
            course_prof_map[course_code] = professors[0]
    
    return course_prof_map

def create_course_professor_map_all(df):
    """
    Create a mapping from course to all professors assigned to it.
    
    :param df: DataFrame with 'G CODE' and 'Professor' columns
    :return: Dictionary mapping course codes to list of professor emails
    """
    course_prof_map = {}
    
    for index, row in df.iterrows():
        course_code = row['G CODE']
        professor_str = row['Professor']
        
        # Handle ampersand-separated professors
        if pd.isna(professor_str):
            continue
            
        professors = [prof.strip() for prof in str(professor_str).split('&')]
        professors = [prof for prof in professors if prof]  # Remove empty strings
        
        if professors:
            course_prof_map[course_code] = professors
    
    return course_prof_map

def get_primary_professor(professor_str):
    """
    Get the primary (first) professor from an ampersand-separated list of professors.
    
    :param professor_str: String containing professor names, possibly ampersand-separated
    :return: Primary professor name
    """
    if pd.isna(professor_str):
        return None
        
    professors = [prof.strip() for prof in str(professor_str).split('&')]
    return professors[0] if professors and professors[0] else None

def get_all_professors(professor_str):
    """
    Get all professors from an ampersand-separated list of professors.
    
    :param professor_str: String containing professor names, possibly ampersand-separated
    :return: List of professor names
    """
    if pd.isna(professor_str):
        return []
        
    professors = [prof.strip() for prof in str(professor_str).split('&')]
    return [prof for prof in professors if prof]  # Remove empty strings
