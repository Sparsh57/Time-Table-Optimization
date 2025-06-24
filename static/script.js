// Global objects to store selected files, preview data, and column mappings
const selectedFiles = {
    courses: null,
    faculty: null,
    students: null
  };
  
  const previewData = {
    courses: [],
    faculty: [],
    students: []
  };
  
  const columnMappings = {
    courses_file: {},
    faculty_preferences_file: {},
    student_courses_file: {}
  };
  
  // Make variables globally accessible
  window.selectedFiles = selectedFiles;
  window.previewData = window.previewData || previewData;
  window.columnMappings = window.columnMappings || columnMappings;

  // Function to sync local data with global window objects
  function syncToGlobal() {
    window.selectedFiles = selectedFiles;
    Object.assign(window.previewData, previewData);
    Object.assign(window.columnMappings, columnMappings);
  }

  // Initialize LoadingManager
  let loadingManager;
  
  // Initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', function() {
    // Use the global loadingManager instance created by loading.js
    if (window.loadingManager) {
      loadingManager = window.loadingManager;
    }
  });
  
  /**
   * Uploads a file for preview and renders the preview and mapping UI.
   * @param {string} fileType - "courses", "faculty", or "students"
   */
    async function previewFile(fileType) {
    const inputElem = document.getElementById(fileType + "Input");
    const file = inputElem.files[0];
    const errorElem = document.getElementById(fileType + "Error");
    const headerElem = document.getElementById(fileType + "Header");
    const bodyElem = document.getElementById(fileType + "Body");
    const mappingElem = document.getElementById(fileType + "Mapping");

    // Reset previous messages and table content
    errorElem.innerText = "";
    headerElem.innerHTML = "";
    bodyElem.innerHTML = "";
    mappingElem.innerHTML = "";

    if (!file) {
      errorElem.innerText = "No file selected.";
      return;
    }

    // Save file for final submission
    selectedFiles[fileType] = file;

    // Show loading screen for preview
    if (loadingManager) {
      loadingManager.showDataUpload();
    }

    let formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType);

    try {
      const response = await fetch("/upload/", {
        method: "POST",
        body: formData
      });
      const data = await response.json();

      if (data.error) {
        errorElem.innerText = data.error;
        return;
      }

      // Save raw preview data for this file type (UPDATE BOTH LOCAL AND GLOBAL)
      previewData[fileType] = data.preview || [];
        window.previewData[fileType] = data.preview || [];

      // Sync to global objects
      syncToGlobal();

      // Render preview table
      renderTable(fileType, data.preview || []);

      // Render mapping UI (if extra or missing columns exist)
      renderMappingUI(fileType, data.extra_cols || [], data.missing_cols || []);
    } catch (err) {
      console.error(`Preview error for ${fileType}:`, err);
      errorElem.innerText = "Preview failed. Check console.";
    } finally {
      // Hide loading screen
      if (loadingManager) {
        loadingManager.hide();
      }
    }
  }
  
  /**
   * Renders the preview table.
   */
  function renderTable(fileType, rows) {
    const headerElem = document.getElementById(fileType + "Header");
    const bodyElem = document.getElementById(fileType + "Body");
    headerElem.innerHTML = "";
    bodyElem.innerHTML = "";

    if (rows.length === 0) {
      return;
    }
  
    const columns = Object.keys(rows[0]);
    columns.forEach(col => {
      const th = document.createElement("th");
      th.innerText = col;
      headerElem.appendChild(th);
    });

    rows.forEach(row => {
      const tr = document.createElement("tr");
      columns.forEach(col => {
        const td = document.createElement("td");
        td.innerText = row[col];
        tr.appendChild(td);
      });
      bodyElem.appendChild(tr);
    });
  }
  
  /**
   * Renders dropdowns for mapping extra columns and displays missing columns.
   */
  function renderMappingUI(fileType, extraCols, missingCols) {
    const mappingElem = document.getElementById(fileType + "Mapping");
    mappingElem.innerHTML = "";
  
    // Map fileType to key used for final submission
    const keyMap = {
      courses: "courses_file",
      faculty: "faculty_preferences_file",
      students: "student_courses_file"
    };
    const fileKey = keyMap[fileType];
  
    // Clear any old mapping
    columnMappings[fileKey] = {};
  
    // Display missing columns info
    if (missingCols.length > 0) {
      const p = document.createElement("p");
      p.innerText = "Missing columns: " + missingCols.join(", ");
      mappingElem.appendChild(p);
    }
  
    // If extra columns exist, create dropdowns for mapping
    if (extraCols.length > 0) {
      const p = document.createElement("p");
      p.innerText = "Extra columns detected:";
      mappingElem.appendChild(p);
  
      // Expected columns for each file type
      const expectedMap = {
        courses: ["Course code", "Faculty Name", "Type", "Credits"],
        faculty: ["Name", "Busy Slot"],
        students: ["Roll No.", "G CODE", "Sections"]
      };
  
      extraCols.forEach(col => {
        const label = document.createElement("label");
        label.innerText = `Map "${col}" → `;
        const select = document.createElement("select");
        // Add browser-default class to ensure the dropdown is visible
        select.classList.add("browser-default");
        select.id = fileType + "_" + col;
  
        const defaultOpt = document.createElement("option");
        defaultOpt.value = "";
        defaultOpt.innerText = "Select expected column";
        select.appendChild(defaultOpt);
  
        expectedMap[fileType].forEach(ec => {
          const opt = document.createElement("option");
          opt.value = ec;
          opt.innerText = ec;
          select.appendChild(opt);
        });
  
        mappingElem.appendChild(label);
        mappingElem.appendChild(select);
        mappingElem.appendChild(document.createElement("br"));
      });
  
      // Add Confirm Mapping button
      const confirmBtn = document.createElement("button");
      confirmBtn.classList.add("btn");
      confirmBtn.innerText = `Confirm Mapping for ${fileType}`;
      confirmBtn.onclick = () => confirmMapping(fileType, extraCols);
      mappingElem.appendChild(confirmBtn);
    } else {
      if (missingCols.length === 0) {
        mappingElem.innerText = "No column mapping needed. Everything matches!";
      }
    }
  }
  
  /**
   * On "Confirm Mapping", this function:
   * - Reads dropdown selections,
   * - Renames the local preview data,
   * - Stores the mapping in the global columnMappings.
   */
    function confirmMapping(fileType, extraCols) {
    const keyMap = {
      courses: "courses_file",
      faculty: "faculty_preferences_file",
      students: "student_courses_file"
    };
    const fileKey = keyMap[fileType];

    let mapping = {};
    extraCols.forEach(col => {
      const select = document.getElementById(fileType + "_" + col);
      if (select && select.value) {
        mapping[col.trim()] = select.value.trim();
      }
    });
    
    // Update both local and global column mappings
    columnMappings[fileKey] = mapping;
    if (!window.columnMappings) {
      window.columnMappings = {
        courses_file: {},
        faculty_preferences_file: {},
        student_courses_file: {}
      };
    }
      window.columnMappings[fileKey] = mapping;

    // Rename keys in local previewData and update table for visual feedback.
    let newPreview = previewData[fileType].map(row => {
      let newRow = {};
      for (let key in row) {
        // If a mapping exists for the column (using trimmed keys)
        if (mapping[key.trim()]) {
          newRow[mapping[key.trim()]] = row[key];
        } else {
          newRow[key] = row[key];
        }
      }
      return newRow;
    });
    
    // Update both local and global preview data
    previewData[fileType] = newPreview;
    if (!window.previewData) {
      window.previewData = {
        courses: [],
        faculty: [],
        students: []
      };
    }
      window.previewData[fileType] = newPreview;

    // Sync to global objects
    syncToGlobal();

    // Re-render preview table with updated column names.
    renderTable(fileType, newPreview);

    alert(`Mapping for ${fileType} applied locally!`);
  }
  
  /**
   * Submits all three files and the column mappings to /send_admin_data.
   */
  async function submitAll() {
    const validationDiv = document.getElementById("submitValidation");
    validationDiv.innerText = ""; // Clear previous errors
    
    // Validate files are selected
    if (!selectedFiles.courses || !selectedFiles.faculty || !selectedFiles.students) {
      const missingFiles = [];
      if (!selectedFiles.courses) missingFiles.push("Courses file");
      if (!selectedFiles.faculty) missingFiles.push("Faculty preferences file");
      if (!selectedFiles.students) missingFiles.push("Student courses file");
      
      validationDiv.innerText = `Missing: ${missingFiles.join(", ")}. Please preview all files first.`;
      alert("Please preview all three files before submitting.");
        return;
    }

    // Validate preview data exists and has content
    if (!previewData.courses || previewData.courses.length === 0) {
      validationDiv.innerText = "Courses file has no data. Please upload a file with valid course data.";
      alert("Courses file has no data. Please upload a file with valid course data.");
      return;
    }
    
    if (!previewData.faculty || previewData.faculty.length === 0) {
      validationDiv.innerText = "Faculty preferences file has no data. Please upload a file with valid faculty data.";
      alert("Faculty preferences file has no data. Please upload a file with valid faculty data.");
      return;
    }
    
    if (!previewData.students || previewData.students.length === 0) {
      validationDiv.innerText = "Student courses file has no data. Please upload a file with valid student enrollment data.";
      alert("Student courses file has no data. Please upload a file with valid student enrollment data.");
      return;
    }

    // Show loading screen for timetable generation
    if (loadingManager) {
      // Check if overlay is empty and force create content if needed
      const overlay = document.getElementById('loading-overlay');
      if (overlay && overlay.childElementCount === 0) {
        if (typeof loadingManager.forceCreateContent === 'function') {
          loadingManager.forceCreateContent();
        } else {
          const htmlContent = `
            <div class="loading-container">
              <div class="loading-spinner">
                <div class="custom-spinner"></div>
              </div>
              <div class="loading-content">
                <h5 id="loading-title">Processing...</h5>
                <p id="loading-message">Please wait while we process your request.</p>
                <small id="loading-time">Elapsed: 0s</small>
              </div>
            </div>
          `;
          overlay.innerHTML = htmlContent;
        }
      }
      
      // Small delay to ensure content is rendered before showing
      setTimeout(() => {
        loadingManager.showTimetableGeneration();
      }, 50);
    } else {
      showSimpleLoading(); // Fallback
    }

    let formData = new FormData();
    formData.append("courses_file", selectedFiles.courses);
    formData.append("faculty_preferences_file", selectedFiles.faculty);
    formData.append("student_courses_file", selectedFiles.students);
    formData.append("column_mappings", JSON.stringify(columnMappings));

    // Append the constraint toggles
    formData.append("toggle_prof",    document.getElementById("toggle_prof").checked);
    formData.append("toggle_capacity",document.getElementById("toggle_capacity").checked);
    formData.append("toggle_student", document.getElementById("toggle_student").checked);
    formData.append("toggle_same_day",document.getElementById("toggle_same_day").checked);
    formData.append("toggle_consec_days", document.getElementById("toggle_consec_days").checked);

    try {
      const response = await fetch("/send_admin_data", {
        method: "POST",
        body: formData,
        redirect: 'manual'  // Don't follow redirects automatically
      });
      
      // Hide loading screen first
      if (loadingManager) {
        loadingManager.hide();
      } else {
        hideSimpleLoading();
      }
      
      // Handle redirects (success case)
      if (response.status === 303 || response.status === 302) {
        // Server wants to redirect to timetable page - this is success
        window.location.href = '/timetable';
        return;
      }
      
      if (response.ok) {
        // Direct success response
        window.location.href = '/timetable';
        return;
      }
      
      // Handle error responses
      let errorMessage = "Unknown error occurred";
      
      try {
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } else {
          // Response is HTML or other format
          const errorText = await response.text();
          // Extract error message from HTML if possible
          if (errorText.includes('detail')) {
            errorMessage = `Server error (${response.status}): Please check your data and try again.`;
          } else {
            errorMessage = `Server error (${response.status}): ${response.statusText}`;
          }
        }
      } catch (parseError) {
        console.error("Error parsing response:", parseError);
        errorMessage = `Server error (${response.status}): ${response.statusText}`;
      }
      
      validationDiv.innerText = errorMessage;
      alert("Error: " + errorMessage);
      
    } catch (err) {
      console.error("Submission error:", err);
      
      // Hide loading screen
      if (loadingManager) {
        loadingManager.hide();
      } else {
        hideSimpleLoading();
      }
      
      const errorMessage = "Submission failed: " + err.message;
      validationDiv.innerText = errorMessage;
      alert(errorMessage);
    }
  }

  // Simple loading screen functions
  function showSimpleLoading() {
    // Remove any existing loading overlay
    const existingOverlay = document.getElementById('simple-loading-overlay');
    if (existingOverlay) {
      existingOverlay.remove();
    }

    // Create a very simple loading overlay
    const overlay = document.createElement('div');
    overlay.id = 'simple-loading-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.8);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-family: Arial, sans-serif;
    `;
    
    overlay.innerHTML = `
      <div style="text-align: center; background: white; color: black; padding: 30px; border-radius: 10px;">
        <div style="width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
        <h3>Generating Timetable</h3>
        <p>Please wait...</p>
      </div>
      <style>
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      </style>
    `;
    
    document.body.appendChild(overlay);
    
    // Force a reflow to ensure the element is rendered
    overlay.offsetHeight;
  }

  function hideSimpleLoading() {
    const overlay = document.getElementById('simple-loading-overlay');
    if (overlay) {
      overlay.remove();
    }
  }
