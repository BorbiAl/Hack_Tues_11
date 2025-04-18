document.addEventListener("DOMContentLoaded", function () {
    const calendar = document.getElementById("calendar");
    const currentMonthYear = document.getElementById("current-month-year");
    const prevMonthButton = document.getElementById("prev-month");
    const nextMonthButton = document.getElementById("next-month");
    const selectedDateSpan = document.getElementById("selected-date");
    const subjectSelect = document.getElementById("subject-select");
    const saveSubjectButton = document.getElementById("save-subject");
  
    let currentDate = new Date();
  
    function renderCalendar() {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth();
  
      // Clear the calendar
      calendar.innerHTML = "";
  
      // Set the current month and year
      currentMonthYear.textContent = `${currentDate.toLocaleString("default", {
        month: "long",
      })} ${year}`;
  
      // Get the first day of the month
      const firstDay = new Date(year, month, 1).getDay();
  
      // Get the number of days in the month
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
  
        // Add click event to select the date
        dayCell.addEventListener("click", function () {
          selectedDateSpan.textContent = `${day} ${currentDate.toLocaleString(
            "default",
            { month: "long" }
          )} ${year}`;
        });
  
        calendar.appendChild(dayCell);
      }
    }
  
    // Event listeners for navigation buttons
    prevMonthButton.addEventListener("click", function () {
      currentDate.setMonth(currentDate.getMonth() - 1);
      renderCalendar();
    });
  
    nextMonthButton.addEventListener("click", function () {
      currentDate.setMonth(currentDate.getMonth() + 1);
      renderCalendar();
    });
  
    // Event listener for saving the subject
    saveSubjectButton.addEventListener("click", function () {
      const selectedSubject = subjectSelect.value;
      const selectedDate = selectedDateSpan.textContent;
  
      if (selectedDate) {
        alert(`Subject "${selectedSubject}" saved for ${selectedDate}!`);
      } else {
        alert("Please select a date first.");
      }
    });
  
    // Initial render
    renderCalendar();
  });