document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.getElementById("calendar");
  if (!calendar) {
    console.error("Calendar element not found. Ensure an element with ID 'calendar' exists in the HTML.");
    return;
  }
  const subjectContainer = document.getElementById("subject-container");
  const selectedDateSpan = document.getElementById("selected-date");
  const saveSubjectButton = document.getElementById("save-subject");
  const subjectSelect = document.getElementById("subject-select");
  const closeMenuButton = document.getElementById("close-menu"); // Add a close button
  let selectedDayCell = null;
  let selectedCellDate = null;

  // Declare currentDate at the top to avoid reference errors
  const currentDate = new Date();

  function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const monthName = currentDate.toLocaleString("default", { month: "long" });
    const yearElement = document.getElementById("calendar-year");
    const monthElement = document.getElementById("calendar-month");

    if (yearElement) {
      yearElement.textContent = year;
    } else {
      console.error("Year element not found. Ensure an element with ID 'calendar-year' exists in the HTML.");
    }

    if (monthElement) {
      monthElement.textContent = monthName;
    } else {
      console.error("Month element not found. Ensure an element with ID 'calendar-month' exists in the HTML.");
    }

    calendar.innerHTML = "";

    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const today = new Date();
    today.setHours(0, 0, 0, 0); // Normalize today's date for comparison

    // Add cells for each day of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const dayCell = document.createElement("div");
      dayCell.classList.add("calendar-day");
      dayCell.textContent = day;

      const cellDate = new Date(year, month, day);
      cellDate.setHours(0, 0, 0, 0); // Normalize for comparison

      // Disable past dates (including today)
      if (cellDate <= today) {
        dayCell.classList.add("disabled");
      } else {
        // Add click event to show the menu for future dates
        dayCell.addEventListener("click", function () {
          // Highlight the selected day
          if (selectedDayCell) {
            selectedDayCell.classList.remove("selected");
          }
          dayCell.classList.add("selected");
          selectedDayCell = dayCell;
          selectedCellDate = cellDate;

          // Update the selected date in the menu
          selectedDateSpan.textContent = `${day}/${month + 1}/${year}`;
          subjectContainer.style.display = "block"; // Show the menu
          saveSubjectButton.disabled = false;
        });
      }

      calendar.appendChild(dayCell);
    }
  }

  function getCSRFToken() {
    const name = 'csrftoken';
    const cookieValue = document.cookie.split('; ')
      .find(row => row.startsWith(name + '='))
      ?.split('=')[1];
    return cookieValue;
  }

  // Save the selected subject and date
  saveSubjectButton.addEventListener("click", async function () {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Double-check that the selected date is in the future
    if (!selectedCellDate || selectedCellDate <= today) {
      alert("You can only schedule tests for future dates.");
      subjectContainer.style.display = "none";
      return;
    }

    const selectedSubject = subjectSelect.value;
    const selectedDate = selectedDateSpan.textContent;

    if (!selectedDate) {
      alert("Please select a date first.");
      return;
    }

    const [day, month, year] = selectedDate.split("/");
    const formattedDate = `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;

    const data = {
      date: formattedDate,
      subject: selectedSubject,
    };

    try {
      const response = await fetch("/save-test/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error("Failed to save test");
      }

      const result = await response.json();
      alert(`Test saved for ${result.date} with subject ${result.subject}`);
      subjectContainer.style.display = "none"; // Hide the menu after saving
    } catch (error) {
      console.error("Error saving test:", error);
      alert("An error occurred while saving the test.");
    }
  });

  // Close the menu when the close button is clicked
  closeMenuButton.addEventListener("click", function () {
    subjectContainer.style.display = "none";
    if (selectedDayCell) {
      selectedDayCell.classList.remove("selected");
    }
    selectedDayCell = null;
    selectedCellDate = null;
  });
  renderCalendar();
});