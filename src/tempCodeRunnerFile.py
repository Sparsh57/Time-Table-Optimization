# Load data
df_registration, df_courses, df_faculty_pref = load_data()
df_merged = merge_data(df_registration, df_courses)
student_course_map = prepare_student_course_map(df_merged)
course_professor_map = create_course_professor_map(df_merged)
professor_busy_slots = faculty_busy_slots(df_faculty_pref)