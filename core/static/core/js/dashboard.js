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
    console.log("Fetching saved tests from: ", url);

    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to fetch saved tests');
        }
        return response.json();
      })
      .then((data) => {
        let savedTests = data.tests || []; // Default to empty array if data.tests is missing
        if (!Array.isArray(savedTests)) {
          console.error("data.tests is not an array:", data.tests);
          return; // Stop processing if it's not an array
        }

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

  function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    calendar.innerHTML = '';

    currentMonthYear.textContent = `${currentDate.toLocaleString('default', {
      month: 'long',
    })} ${year}`;

    // Disable previous button if we are on the current month
    if (month === today.getMonth() && year === today.getFullYear()) {
      prevMonthButton.style.display = 'none'; // or use .disabled = true;
    } else {
      prevMonthButton.style.display = 'inline-block';
    }

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const prevMonthLastDate = new Date(year, month, 0).getDate();
    const startOffset = firstDay === 0 ? 6 : firstDay - 1; // Adjust if week starts on Monday

    for (let i = startOffset; i > 0; i--) {
      const emptyCell = document.createElement('div');
      emptyCell.classList.add('calendar-day', 'empty', 'prev-month', 'past-date');
      emptyCell.textContent = prevMonthLastDate - i + 1;

      const prevDate = new Date(year, month - 1, prevMonthLastDate - i + 1);
      emptyCell.setAttribute('data-date', prevDate.toISOString().split('T')[0]);

      calendar.appendChild(emptyCell);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dayCell = document.createElement('div');
      dayCell.classList.add('calendar-day');
      dayCell.textContent = day;

      const date = new Date(year, month, day);
      date.setHours(0, 0, 0, 0); // Normalize

      const dateString = date.toISOString().split('T')[0];
      dayCell.setAttribute('data-date', dateString);

      if (date < today) {
        dayCell.classList.add('past-date');
      } else {
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
      }

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

    const [day, month, year] = selectedDate.split('/').map((part) => part.padStart(2, '0'));

    const selectedDateObj = new Date(`${year}-${month}-${day}`);
    selectedDateObj.setDate(selectedDateObj.getDate() - 1);
    const formattedDate = selectedDateObj.toISOString().split('T')[0];



    const data = {
      date: formattedDate,
      subject: selectedSubject,
    };

    fetch('/save-subject/', {
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
        location.reload();
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

  const courseCard = document.querySelector('.course-card');

  const daysLeft = parseInt(document.getElementById('days-left').textContent, 10);

  if (courseCard && daysLeft !== Infinity) {
    courseCard.addEventListener('click', () => {
      window.location.href = '/test-textbook/';
    });
  }

  const welcomeCard = document.querySelector('.welcome-card');
  if (welcomeCard) {
    welcomeCard.addEventListener('click', () => {
      window.location.href = '/profile/';
    });
  }
});

