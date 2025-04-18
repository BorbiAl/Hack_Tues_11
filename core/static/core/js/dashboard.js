document.addEventListener('DOMContentLoaded', function () {
  const calendar = document.getElementById('calendar');
  const currentMonthYear = document.getElementById('current-month-year');
  const prevMonthButton = document.getElementById('prev-month');
  const nextMonthButton = document.getElementById('next-month');
  const selectedDateSpan = document.getElementById('selected-date');
  const subjectSelect = document.getElementById('subject-select');
  const saveSubjectButton = document.getElementById('save-subject');
  const subjectContainer = document.getElementById('subject-container');

  let currentDate = new Date();
  let selectedDayCell = null;

  // Function to get CSRF token
  function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
  }

  // Fetch saved tests from the backend
  function fetchSavedTests(month, year) {
    const url = `/saved-tests/?month=${month}&year=${year}`;

    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch saved tests');
        }
        return response.json();
      })
      .then((data) => {
        const savedTests = data.tests || [];
        savedTests.forEach((test) => {
          const testDate = new Date(test.date);
          const dayCell = document.querySelector(
            `.calendar-day[data-date="${testDate.toISOString().split('T')[0]}"]`
          );
          if (dayCell) {
            dayCell.classList.add('test-saved');
            dayCell.setAttribute('data-subject', test.subject);
          }
        });
      })
      .catch((error) => {
        console.error('Error fetching saved tests:', error);
      });
  }

  // Render the calendar
  function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    calendar.innerHTML = '';

    currentMonthYear.textContent = `${currentDate.toLocaleString('default', {
      month: 'long',
    })} ${year}`;

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
      const emptyCell = document.createElement('div');
      emptyCell.classList.add('calendar-day', 'empty');
      calendar.appendChild(emptyCell);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dayCell = document.createElement('div');
      dayCell.classList.add('calendar-day');
      dayCell.textContent = day;

      const date = new Date(year, month, day);
      dayCell.setAttribute('data-date', date.toISOString().split('T')[0]);

      dayCell.addEventListener('click', function () {
        selectedDateSpan.textContent = `${day}/${month + 1}/${year}`;
        subjectContainer.style.display = 'block'; 
        saveSubjectButton.disabled = false;
      
        if (selectedDayCell) {
          selectedDayCell.classList.remove('selected');
        }
        dayCell.classList.add('selected');
        selectedDayCell = dayCell;
      });

      calendar.appendChild(dayCell);
    }

    fetchSavedTests(month + 1, year);
  }

  // Save the selected subject and date to the backend
  saveSubjectButton.addEventListener('click', function () {
    console.log('Save Subject button clicked'); // Debugging log
    const selectedSubject = subjectSelect.value;
    const selectedDate = selectedDateSpan.textContent;
  
    if (!selectedDate) {
      alert('Please select a date first.');
      return;
    }
  
    const [day, month, year] = selectedDate.split('/');
    const formattedDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`; // Format as YYYY-MM-DD
  
    const data = {
      date: formattedDate,
      subject: selectedSubject,
    };
  
    fetch('/save-test/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify(data),
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to save test');
        }
        return response.json();
      })
      .then((data) => {
        alert(`Test saved for ${data.date} with subject ${data.subject}`);
        renderCalendar(); // Re-render the calendar to reflect the saved test
      })
      .catch((error) => {
        console.error('Error saving test:', error);
      });
  });

  // Event listeners for navigation buttons
  prevMonthButton.addEventListener('click', function () {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
  });

  nextMonthButton.addEventListener('click', function () {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
  });

  // Initial render
  renderCalendar();
});