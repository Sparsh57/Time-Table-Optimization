import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from .dbconnection import get_db_session, is_postgresql, get_organization_database_url
from .models import User, Course, CourseStud
import logging
from sqlalchemy import func
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


def get_optimal_k(student_course_matrix, student_matrix, max_k=10):
    """
    Find the optimal number of clusters using elbow method and silhouette score.
    
    :param student_course_matrix: DataFrame with student-course enrollment data
    :param student_matrix: Numpy array of the student-course matrix
    :param max_k: Maximum number of clusters to test
    :return: Optimal number of clusters
    """
    if len(student_course_matrix) < 4:  # Need at least 4 students for meaningful clustering
        return min(2, len(student_course_matrix))
    
    max_k = min(max_k, len(student_course_matrix) // 2)  # Ensure reasonable upper bound
    
    if max_k < 2:
        return 2
    
    silhouette_scores = []
    k_range = range(2, max_k + 1)
    
    for k in k_range:
        try:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(student_matrix)
            silhouette_avg = silhouette_score(student_matrix, cluster_labels)
            silhouette_scores.append(silhouette_avg)
        except Exception as e:
            logger.warning(f"Error computing silhouette score for k={k}: {e}")
            silhouette_scores.append(0)
    
    # Find k with highest silhouette score
    optimal_k = k_range[np.argmax(silhouette_scores)]
    return optimal_k


def get_multi_section_courses(db_path):
    """
    Get courses that have multiple sections.
    
    :param db_path: Path to the database or schema identifier
    :return: Dictionary mapping course names to number of sections
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            courses = session.query(Course).filter(Course.NumberOfSections > 1).all()
            return {course.CourseName: course.NumberOfSections for course in courses}
        except Exception as e:
            logger.error(f"Error fetching multi-section courses: {e}")
            return {}


def create_student_course_matrix(db_path):
    """
    Create a student-course matrix for clustering analysis.
    
    :param db_path: Path to the database or schema identifier
    :return: DataFrame with students as rows and courses as columns (pivot table)
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            # Get all student enrollments
            query = session.query(
                User.Email.label('Roll_No'),
                Course.CourseName.label('G_CODE')
            ).select_from(CourseStud)\
             .join(User, CourseStud.StudentID == User.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .filter(User.Role == 'Student')
            
            df = pd.DataFrame(query.all())
            
            if df.empty:
                logger.warning("No student enrollment data found")
                return pd.DataFrame()
            
            # Extract base course names from section identifiers if they exist in G_CODE
            def extract_base_course(course_identifier):
                """Extract base course name from section identifier like DATA201-A -> DATA201"""
                if '-' in course_identifier and course_identifier.split('-')[-1].isalpha():
                    parts = course_identifier.split('-')
                    if len(parts[-1]) == 1:  # Single letter section identifier
                        return '-'.join(parts[:-1])
                return course_identifier
            
            df['BaseCourse'] = df['G_CODE'].apply(extract_base_course)
            
            # Create pivot table using base course names
            student_course_matrix = df.pivot_table(
                index="Roll_No", 
                columns="BaseCourse", 
                aggfunc=lambda x: 1, 
                fill_value=0
            )
            
            # Flatten column index if it's a MultiIndex
            if isinstance(student_course_matrix.columns, pd.MultiIndex):
                student_course_matrix.columns = student_course_matrix.columns.get_level_values(-1)
            
            return student_course_matrix
            
        except Exception as e:
            logger.error(f"Error creating student-course matrix: {e}")
            return pd.DataFrame()


def allocate_sections_for_course(course_name, num_sections, enrolled_students_df, max_section_size=None):
    """
    Allocate students to sections for a specific course using clustering.
    Ensures all sections are used when possible.
    
    :param course_name: Name of the course
    :param num_sections: Number of sections for the course
    :param enrolled_students_df: DataFrame with students enrolled in this course
    :param max_section_size: Maximum students per section (calculated if None)
    :return: List of dictionaries with section assignments
    """
    if enrolled_students_df.empty:
        return []
    
    enrolled_students = enrolled_students_df.reset_index()[["Roll_No", "Cluster"]]
    total_students = len(enrolled_students)
    
    if max_section_size is None:
        max_section_size = max(10, total_students // num_sections)
    
    logger.info(f"Allocating {total_students} students to {num_sections} sections for {course_name}")
    logger.info(f"Max section size: {max_section_size}")
    
    section_assignments = []
    
    # Group students by cluster
    grouped_students = enrolled_students.groupby("Cluster")["Roll_No"].apply(list)
    
    # Create section counters to track how many students are in each section
    section_counts = [0] * num_sections
    
    # For small clusters or when we want to ensure all sections are used,
    # we'll use a more balanced approach
    all_students = []
    for cluster, students in grouped_students.items():
        for student in students:
            all_students.append({
                "Roll_No": student,
                "Cluster": cluster
            })
    
    # Sort students by cluster to keep similar students together when possible
    all_students.sort(key=lambda x: x["Cluster"])
    
    # If we have fewer students than sections, just distribute one per section
    if total_students <= num_sections:
        for i, student_info in enumerate(all_students):
            section_num = i + 1
            section_assignments.append({
                "Roll_No": student_info["Roll_No"],
                "Course": course_name,
                "Cluster": student_info["Cluster"],
                "Assigned_Section": section_num
            })
            section_counts[i] += 1
        
        logger.info(f"Small class: distributed {total_students} students across {total_students} sections")
    
    # If we have more students than sections, use a balanced distribution
    else:
        # Calculate target size per section
        base_size = total_students // num_sections
        extra_students = total_students % num_sections
        
        # Create target sizes for each section
        target_sizes = [base_size + (1 if i < extra_students else 0) for i in range(num_sections)]
        
        logger.info(f"Target section sizes: {target_sizes}")
        
        # Distribute students trying to keep clusters together when possible
        student_index = 0
        
        for section_idx in range(num_sections):
            target_size = target_sizes[section_idx]
            section_num = section_idx + 1
            
            # Fill this section up to its target size
            students_added = 0
            while students_added < target_size and student_index < total_students:
                student_info = all_students[student_index]
                
                section_assignments.append({
                    "Roll_No": student_info["Roll_No"],
                    "Course": course_name,
                    "Cluster": student_info["Cluster"],
                    "Assigned_Section": section_num
                })
                
                section_counts[section_idx] += 1
                students_added += 1
                student_index += 1
            
            logger.info(f"Section {section_num}: assigned {students_added} students")
    
    # Log final distribution
    logger.info(f"Final section distribution for {course_name}:")
    for i in range(num_sections):
        logger.info(f"  Section {i+1}: {section_counts[i]} students")
    
    # Verify all students were assigned
    total_assigned = sum(section_counts)
    if total_assigned != total_students:
        logger.error(f"Mismatch! {total_students} students but {total_assigned} assignments")
    
    return section_assignments


def allocate_all_sections(db_path):
    """
    Allocate students to sections for all multi-section courses.
    
    :param db_path: Path to the database or schema identifier
    :return: List of all section assignments
    """
    logger.info("Starting section allocation process")
    
    # Create student-course matrix
    student_course_matrix = create_student_course_matrix(db_path)
    
    if student_course_matrix.empty:
        logger.warning("No student-course data available for section allocation")
        return []
    
    # Convert to numpy for clustering
    student_matrix = student_course_matrix.to_numpy()
    
    # Find optimal number of clusters
    optimal_k = get_optimal_k(student_course_matrix, student_matrix)
    logger.info(f"Optimal number of clusters: {optimal_k}")
    
    # Run KMeans clustering
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    student_clusters = kmeans.fit_predict(student_matrix)
    
    # Add cluster information to the matrix
    student_course_matrix["Cluster"] = student_clusters
    
    # Get multi-section courses
    multi_section_courses = get_multi_section_courses(db_path)
    
    all_section_assignments = []
    
    # Allocate sections for each multi-section course
    for course_name, num_sections in multi_section_courses.items():
        logger.info(f"Allocating sections for course {course_name} ({num_sections} sections)")
        
        # Get students enrolled in this course
        enrolled_students = student_course_matrix[student_course_matrix[course_name] == 1]
        
        # Allocate sections for this course
        course_assignments = allocate_sections_for_course(
            course_name, num_sections, enrolled_students
        )
        
        all_section_assignments.extend(course_assignments)
        logger.info(f"Allocated {len(course_assignments)} students to sections for {course_name}")
    
    return all_section_assignments


def update_student_sections_in_db(section_assignments, db_path):
    """
    Update the database with section assignments using bulk operations.
    
    :param section_assignments: List of section assignment dictionaries
    :param db_path: Path to the database or schema identifier
    """
    if not section_assignments:
        logger.info("No section assignments to update")
        return
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            # First, get all relevant student and course mappings in bulk
            logger.info(f"Preparing bulk section assignment update for {len(section_assignments)} assignments...")
            
            # Extract unique emails and course names
            student_emails = list(set(assignment["Roll_No"] for assignment in section_assignments))
            course_names = list(set(assignment["Course"] for assignment in section_assignments))
            
            # Get student ID mappings
            students_query = session.query(User.Email, User.UserID).filter(
                User.Email.in_(student_emails),
                User.Role == 'Student'
            )
            student_id_map = {email: user_id for email, user_id in students_query.all()}
            
            # Get course ID mappings
            courses_query = session.query(Course.CourseName, Course.CourseID).filter(
                Course.CourseName.in_(course_names)
            )
            course_id_map = {course_name: course_id for course_name, course_id in courses_query.all()}
            
            # Get all relevant CourseStud records
            student_course_pairs = []
            for assignment in section_assignments:
                student_email = assignment["Roll_No"]
                course_name = assignment["Course"]
                student_id = student_id_map.get(student_email)
                course_id = course_id_map.get(course_name)
                
                if student_id and course_id:
                    student_course_pairs.append((student_id, course_id, assignment["Assigned_Section"]))
                else:
                    logger.warning(f"Student {student_email} or course {course_name} not found")
            
            if not student_course_pairs:
                logger.warning("No valid student-course pairs found for section assignments")
                return
            
            # Build conditions for bulk CourseStud lookup
            student_ids = [pair[0] for pair in student_course_pairs]
            course_ids = [pair[1] for pair in student_course_pairs]
            
            # Get all relevant CourseStud records
            course_stud_records = session.query(CourseStud.CourseID, CourseStud.StudentID).filter(
                CourseStud.StudentID.in_(student_ids),
                CourseStud.CourseID.in_(course_ids)
            ).all()
            
            # Create mapping for quick lookup
            course_stud_map = {(record.StudentID, record.CourseID): (record.CourseID, record.StudentID) for record in course_stud_records}
            
            # Prepare bulk update data
            update_cases = []
            course_stud_pairs = []
            
            for student_id, course_id, section_number in student_course_pairs:
                if (student_id, course_id) in course_stud_map:
                    course_stud_pairs.append((course_id, student_id, section_number))
                    update_cases.append(f"WHEN (\"CourseID\" = {course_id} AND \"StudentID\" = {student_id}) THEN {section_number}")
                else:
                    logger.warning(f"CourseStud record not found for StudentID {student_id}, CourseID {course_id}")
            
            if not course_stud_pairs:
                logger.warning("No valid CourseStud records found for section assignments")
                return
            
            # Execute bulk update using CASE statement with composite key
            case_statement = " ".join(update_cases)
            
            if is_postgresql() and org_name:
                # PostgreSQL syntax with composite key
                bulk_update_sql = f"""
                UPDATE "Course_Stud" 
                SET "SectionNumber" = CASE 
                    {case_statement}
                    ELSE "SectionNumber"
                END
                WHERE ("CourseID", "StudentID") IN ({','.join(f'({pair[0]}, {pair[1]})' for pair in course_stud_pairs)})
                """
            else:
                # SQLite syntax with composite key
                bulk_update_sql = f"""
                UPDATE Course_Stud 
                SET SectionNumber = CASE 
                    {case_statement}
                    ELSE SectionNumber
                END
                WHERE (CourseID, StudentID) IN ({','.join(f'({pair[0]}, {pair[1]})' for pair in course_stud_pairs)})
                """
            
            # Execute the bulk update
            result = session.execute(text(bulk_update_sql))
            updated_count = result.rowcount
            
            session.commit()
            logger.info(f"✅ Bulk updated {updated_count} section assignments in database")
            print(f"✅ Successfully updated {updated_count} student section assignments using bulk operations")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error in bulk updating section assignments: {e}")
            raise


def print_section_assignments(section_assignments, title="Section Assignments"):
    """
    Print section assignments in a formatted table.
    
    :param section_assignments: List of section assignment dictionaries
    :param title: Title for the output
    """
    if not section_assignments:
        print("No section assignments to display.")
        return
    
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}")
    
    # Group assignments by course
    course_assignments = {}
    for assignment in section_assignments:
        course_name = assignment["Course"]
        if course_name not in course_assignments:
            course_assignments[course_name] = {}
        
        section_num = assignment["Assigned_Section"]
        if section_num not in course_assignments[course_name]:
            course_assignments[course_name][section_num] = []
        
        course_assignments[course_name][section_num].append(assignment["Roll_No"])
    
    # Print assignments for each course
    for course_name in sorted(course_assignments.keys()):
        print(f"\n📚 Course: {course_name}")
        print("-" * 50)
        
        sections = course_assignments[course_name]
        for section_num in sorted(sections.keys()):
            students = sorted(sections[section_num])
            print(f"  Section {section_num} ({len(students)} students):")
            
            # Print students in columns for better readability
            students_per_row = 3
            for i in range(0, len(students), students_per_row):
                student_group = students[i:i + students_per_row]
                formatted_students = [f"    • {student:<20}" for student in student_group]
                print("".join(formatted_students))
        
        # Print section summary
        total_students = sum(len(students) for students in sections.values())
        print(f"  📊 Total students in {course_name}: {total_students}")
    
    print(f"\n{'='*60}")
    total_assignments = len(section_assignments)
    total_courses = len(course_assignments)
    print(f"📈 Summary: {total_assignments} students assigned across {total_courses} courses")
    print(f"{'='*60}")


def print_detailed_section_mapping(db_path):
    """
    Print detailed section mapping from the database including cluster information.
    
    :param db_path: Path to the database or schema identifier
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            # Get detailed student section information
            query = session.query(
                User.Email.label('Roll_No'),
                User.Name.label('Student_Name'),
                Course.CourseName.label('Course'),
                Course.NumberOfSections,
                CourseStud.SectionNumber
            ).select_from(CourseStud)\
             .join(User, CourseStud.StudentID == User.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .filter(User.Role == 'Student')\
             .filter(Course.NumberOfSections > 1)\
             .order_by(Course.CourseName, CourseStud.SectionNumber, User.Email)
            
            df = pd.DataFrame(query.all())
            
            if df.empty:
                print("\n🔍 No multi-section courses found in the database.")
                return
            
            print(f"\n{'='*80}")
            print(f"{'DETAILED STUDENT-SECTION MAPPING':^80}")
            print(f"{'='*80}")
            
            # Group by course
            for course_name in df['Course'].unique():
                course_data = df[df['Course'] == course_name]
                num_sections = course_data['NumberOfSections'].iloc[0]
                
                print(f"\n📚 Course: {course_name} ({num_sections} sections)")
                print("-" * 70)
                
                # Group by section
                for section_num in sorted(course_data['SectionNumber'].unique()):
                    section_students = course_data[course_data['SectionNumber'] == section_num]
                    print(f"\n  🏫 Section {section_num} ({len(section_students)} students):")
                    
                    # Print students with names if available
                    for _, student in section_students.iterrows():
                        student_name = student['Student_Name'] if student['Student_Name'] != student['Roll_No'] else "N/A"
                        print(f"    • {student['Roll_No']:<25} ({student_name})")
                
                # Print course statistics
                print(f"\n  📊 Course Statistics:")
                section_counts = course_data.groupby('SectionNumber').size()
                for section_num, count in section_counts.items():
                    print(f"    - Section {section_num}: {count} students")
                
                avg_section_size = len(course_data) / num_sections
                print(f"    - Average section size: {avg_section_size:.1f} students")
            
            print(f"\n{'='*80}")
            
        except Exception as e:
            logger.error(f"Error printing detailed section mapping: {e}")


def export_section_mapping_to_csv(db_path, filename=None):
    """
    Export student section mapping to a CSV file.
    
    :param db_path: Path to the database or schema identifier
    :param filename: Output filename (auto-generated if None)
    :return: Filename of the exported CSV
    """
    if filename is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"student_section_mapping_{timestamp}.csv"
    
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            query = session.query(
                User.Email.label('Roll_No'),
                User.Name.label('Student_Name'),
                Course.CourseName.label('Course'),
                Course.NumberOfSections,
                CourseStud.SectionNumber
            ).select_from(CourseStud)\
             .join(User, CourseStud.StudentID == User.UserID)\
             .join(Course, CourseStud.CourseID == Course.CourseID)\
             .filter(User.Role == 'Student')\
             .order_by(Course.CourseName, CourseStud.SectionNumber, User.Email)
            
            df = pd.DataFrame(query.all())
            
            if not df.empty:
                # Add a formatted course-section identifier
                df['Course_Section'] = df.apply(
                    lambda row: f"{row['Course']}-{chr(ord('A') + row['SectionNumber'] - 1)}" 
                    if row['NumberOfSections'] > 1 else row['Course'], 
                    axis=1
                )
                
                # Reorder columns for better CSV output
                df = df[['Roll_No', 'Student_Name', 'Course', 'SectionNumber', 'Course_Section', 'NumberOfSections']]
                
                df.to_csv(filename, index=False)
                print(f"✅ Student section mapping exported to: {filename}")
                print(f"📊 Total records exported: {len(df)}")
                return filename
            else:
                print("❌ No student enrollment data found to export.")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting section mapping: {e}")
            return None


def run_section_allocation(db_path, print_mapping=True, export_csv=False):
    """
    Main function to run the complete section allocation process.
    
    :param db_path: Path to the database or schema identifier
    :param print_mapping: Whether to print the section mapping after allocation
    :param export_csv: Whether to export the section mapping to CSV
    :return: List of section assignments
    """
    try:
        # Generate section assignments
        section_assignments = allocate_all_sections(db_path)
        
        if section_assignments:
            # Update database with assignments
            update_student_sections_in_db(section_assignments, db_path)
            logger.info("Section allocation completed successfully")
            
            # Print section assignments if requested
            if print_mapping:
                print_section_assignments(section_assignments, "🎯 Section Allocation Results")
                print_detailed_section_mapping(db_path)
            
            # Export to CSV if requested
            if export_csv:
                export_section_mapping_to_csv(db_path)
                
        else:
            logger.info("No section assignments needed")
            if print_mapping:
                print("\n🔍 No multi-section courses found - no section allocation needed.")
        
        return section_assignments
        
    except Exception as e:
        logger.error(f"Error in section allocation process: {e}")
        raise


def get_section_allocation_summary(db_path):
    """
    Get a summary of section allocation statistics.
    
    :param db_path: Path to the database or schema identifier
    :return: Dictionary with allocation summary
    """
    # Auto-detect org_name from db_path if it's a schema path
    org_name = None
    if db_path and db_path.startswith("schema:"):
        schema_name = db_path.replace("schema:", "")
        if schema_name.startswith("org_"):
            org_name = schema_name[4:]  # Remove 'org_' prefix

    # Determine which session to use
    if is_postgresql() and org_name:
        session_context = get_db_session(get_organization_database_url(), org_name)
    else:
        session_context = get_db_session(db_path)

    with session_context as session:
        try:
            # Get multi-section courses and their enrollments
            query = session.query(
                Course.CourseName,
                Course.NumberOfSections,
                CourseStud.SectionNumber,
                func.count(CourseStud.StudentID).label('StudentCount')
            ).select_from(Course)\
             .join(CourseStud, Course.CourseID == CourseStud.CourseID)\
             .filter(Course.NumberOfSections > 1)\
             .group_by(Course.CourseName, Course.NumberOfSections, CourseStud.SectionNumber)\
             .order_by(Course.CourseName, CourseStud.SectionNumber)
            
            results = query.all()
            
            summary = {
                'total_multi_section_courses': 0,
                'total_sections': 0,
                'total_students_in_sections': 0,
                'courses': {},
                'section_size_stats': {
                    'min': float('inf'),
                    'max': 0,
                    'avg': 0
                }
            }
            
            section_sizes = []
            
            for row in results:
                course_name = row.CourseName
                if course_name not in summary['courses']:
                    summary['courses'][course_name] = {
                        'num_sections': row.NumberOfSections,
                        'sections': {}
                    }
                    summary['total_multi_section_courses'] += 1
                
                summary['courses'][course_name]['sections'][row.SectionNumber] = row.StudentCount
                summary['total_sections'] += 1
                summary['total_students_in_sections'] += row.StudentCount
                section_sizes.append(row.StudentCount)
            
            if section_sizes:
                summary['section_size_stats']['min'] = min(section_sizes)
                summary['section_size_stats']['max'] = max(section_sizes)
                summary['section_size_stats']['avg'] = sum(section_sizes) / len(section_sizes)
            else:
                summary['section_size_stats'] = {'min': 0, 'max': 0, 'avg': 0}
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting section allocation summary: {e}")
            return {}


def print_section_allocation_summary(db_path):
    """
    Print a formatted summary of section allocation.
    
    :param db_path: Path to the database or schema identifier
    """
    summary = get_section_allocation_summary(db_path)
    
    if not summary or not summary['courses']:
        print("\n🔍 No multi-section courses found in the database.")
        return
    
    print(f"\n{'='*70}")
    print(f"{'📊 SECTION ALLOCATION SUMMARY':^70}")
    print(f"{'='*70}")
    
    print(f"📚 Multi-section courses: {summary['total_multi_section_courses']}")
    print(f"🏫 Total sections: {summary['total_sections']}")
    print(f"👥 Total students in sections: {summary['total_students_in_sections']}")
    
    stats = summary['section_size_stats']
    print(f"📈 Section size - Min: {stats['min']}, Max: {stats['max']}, Avg: {stats['avg']:.1f}")
    
    print(f"\n{'Course Details':^70}")
    print("-" * 70)
    
    for course_name, course_data in summary['courses'].items():
        print(f"\n📚 {course_name} ({course_data['num_sections']} sections):")
        for section_num, student_count in course_data['sections'].items():
            print(f"  Section {section_num}: {student_count} students")
        
        total_students = sum(course_data['sections'].values())
        avg_size = total_students / course_data['num_sections']
        print(f"  📊 Total: {total_students} students (avg: {avg_size:.1f} per section)")
    
    print(f"\n{'='*70}") 