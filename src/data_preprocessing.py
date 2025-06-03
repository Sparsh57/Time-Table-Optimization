import pandas as pd

def merge_data(df_registration, df_courses):
    df_merged = pd.merge(df_registration, df_courses, left_on='G CODE', right_on='Course code', how='left')
    df_merged['Professor'] = df_merged['Faculty Name']
    df_merged = df_merged[['Roll No.','G CODE', 'Professor']]
    return df_merged.dropna()

def prepare_student_course_map(df):
    return {roll: list(group['G CODE']) for roll, group in df.groupby('Roll No.')}

def prepare_student_course_section_map(df):
    """
    Create a mapping from student to courses with section information.
    
    :param df: DataFrame with 'Roll No.' and 'G CODE' columns where G CODE already contains section identifiers
    :return: Dictionary mapping student roll numbers to list of course identifiers
    """
    student_course_section_map = {}
    
    for roll, group in df.groupby('Roll No.'):
        courses_sections = []
        for _, row in group.iterrows():
            # G CODE already contains the properly formatted section identifier from the database query
            course_identifier = row['G CODE']
            courses_sections.append(course_identifier)
        student_course_section_map[roll] = courses_sections
    
    return student_course_section_map

def expand_courses_with_sections(df):
    """
    Expand courses with multiple sections into separate course-section entries.
    
    :param df: DataFrame with course data including section information
    :return: DataFrame with expanded course-section entries
    """
    expanded_rows = []
    
    for index, row in df.iterrows():
        course_code = row['G CODE']
        num_sections = row.get('NumberOfSections', 1)
        professors = row.get('Professor', '')
        
        # Parse professors
        if pd.isna(professors):
            prof_list = []
        else:
            prof_list = [prof.strip() for prof in str(professors).split(',') if prof.strip()]
        
        # Create entries for each section
        for section_num in range(1, int(num_sections) + 1):
            # Assign professor using round-robin
            if prof_list:
                prof_index = (section_num - 1) % len(prof_list)
                assigned_professor = prof_list[prof_index]
            else:
                assigned_professor = ''
            
            # Create new row for this section
            new_row = row.copy()
            
            # Format course identifier based on number of sections
            if num_sections == 1:
                # Single section: just use course name
                new_row['G CODE'] = course_code
            else:
                # Multiple sections: use course-A, course-B format
                section_letter = chr(ord('A') + section_num - 1)  # Convert 1->A, 2->B, etc.
                new_row['G CODE'] = f"{course_code}-{section_letter}"
            
            new_row['BaseCourse'] = course_code
            new_row['SectionNumber'] = section_num
            new_row['Professor'] = assigned_professor
            
            expanded_rows.append(new_row)
    
    return pd.DataFrame(expanded_rows)

def create_course_professor_map(df):
    """
    Create a mapping from course to professor.
    If multiple professors are assigned to a course (comma-separated), 
    takes the first professor for backward compatibility with existing algorithm.
    
    :param df: DataFrame with 'G CODE' and 'Professor' columns
    :return: Dictionary mapping course codes to professor emails
    """
    course_prof_map = {}
    
    for index, row in df.iterrows():
        course_code = row['G CODE']
        professor_str = row['Professor']
        
        # Handle comma-separated professors by taking the first one
        if pd.isna(professor_str):
            continue
            
        professors = [prof.strip() for prof in str(professor_str).split(',')]
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
        
        # Handle comma-separated professors
        if pd.isna(professor_str):
            continue
            
        professors = [prof.strip() for prof in str(professor_str).split(',')]
        professors = [prof for prof in professors if prof]  # Remove empty strings
        
        if professors:
            course_prof_map[course_code] = professors
    
    return course_prof_map

def get_primary_professor(professor_str):
    """
    Get the primary (first) professor from a comma-separated list of professors.
    
    :param professor_str: String containing professor names, possibly comma-separated
    :return: Primary professor name
    """
    if pd.isna(professor_str):
        return None
        
    professors = [prof.strip() for prof in str(professor_str).split(',')]
    return professors[0] if professors and professors[0] else None

def get_all_professors(professor_str):
    """
    Get all professors from a comma-separated list of professors.
    
    :param professor_str: String containing professor names, possibly comma-separated
    :return: List of professor names
    """
    if pd.isna(professor_str):
        return []
        
    professors = [prof.strip() for prof in str(professor_str).split(',')]
    return [prof for prof in professors if prof]  # Remove empty strings
