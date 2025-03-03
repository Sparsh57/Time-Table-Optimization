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
      }
  
      // Save raw preview data for this file type
      previewData[fileType] = data.preview || [];
  
      // Render preview table
      renderTable(fileType, data.preview || []);
  
      // Render mapping UI (if extra or missing columns exist)
      renderMappingUI(fileType, data.extra_cols || [], data.missing_cols || []);
    } catch (err) {
      console.error("Preview error:", err);
      errorElem.innerText = "Preview failed. Check console.";
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
    if (rows.length === 0) return;
  
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
    columnMappings[fileKey] = mapping;
    console.log("Mapping for", fileType, ":", mapping);
  
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
    previewData[fileType] = newPreview;
  
    // Re-render preview table with updated column names.
    renderTable(fileType, newPreview);
  
    alert(`Mapping for ${fileType} applied locally!`);
  }
  
  /**
   * Submits all three files and the column mappings to /send_admin_data.
   */
  async function submitAll() {
    if (!selectedFiles.courses || !selectedFiles.faculty || !selectedFiles.students) {
      alert("Please preview all three files before submitting.");
      return;
    }
  
    let formData = new FormData();
    formData.append("courses_file", selectedFiles.courses);
    formData.append("faculty_preferences_file", selectedFiles.faculty);
    formData.append("student_courses_file", selectedFiles.students);
  
    // Send final column mappings as JSON
    formData.append("column_mappings", JSON.stringify(columnMappings));
  
    try {
      const response = await fetch("/send_admin_data", {
        method: "POST",
        body: formData
      });
      if (response.redirected) {
        window.location.href = response.url;
      } else {
        const data = await response.json();
        alert("Final submission response: " + JSON.stringify(data));
      }
    } catch (err) {
      console.error("Submission error:", err);
      alert("Submission failed. Check console for details.");
    }
  }
  