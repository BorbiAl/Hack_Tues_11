document.addEventListener("DOMContentLoaded", function () {
  const calendar = document.getElementById("calendar");
  const subjectContainer = document.getElementById("subject-container");
  const selectedDateSpan = document.getElementById("selected-date");
  const saveSubjectButton = document.getElementById("save-subject");
  const subjectSelect = document.getElementById("subject-select");
  let selectedDayCell = null;

  function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    calendar.innerHTML = "";

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Add empty cells for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
      const emptyCell = document.createElement("div");
      emptyCell.classList.add("calendar-day", "empty");
      calendar.appendChild(emptyCell);
    }

    // Add cells for each day of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const dayCell = document.createElement("div");
      dayCell.classList.add("calendar-day");
      dayCell.textContent = day;

      // Add click event to show the menu
      dayCell.addEventListener("click", function () {
        // Highlight the selected day
        if (selectedDayCell) {
          selectedDayCell.classList.remove("selected");
        }
        dayCell.classList.add("selected");
        selectedDayCell = dayCell;

        // Update the selected date in the menu
        selectedDateSpan.textContent = `${day}/${month + 1}/${year}`;
        subjectContainer.style.display = "block";
        saveSubjectButton.disabled = false; // Enable the save button
      });

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
    const selectedSubject = subjectSelect.value;
    const selectedDate = selectedDateSpan.textContent;

    if (!selectedDate) {
      alert("Please select a date first.");
      return;
    }

    const [day, month, year] = selectedDate.split("/");
    const formattedDate = `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`; // Format as YYYY-MM-DD

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
    }
  });

  // Initial render
  const currentDate = new Date();
  renderCalendar();
});