document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("generateTestForm");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const resultDiv = document.getElementById("result");

    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent the form from reloading the page
        loadingIndicator.style.display = "block"; // Show the loading indicator

        const formData = new FormData(form); // Capture form data

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute('content'), // Include CSRF token
                },
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    resultDiv.innerHTML = `<pre>${data.test}</pre>`; // Display the test
                } else {
                    resultDiv.innerHTML = `<p>Error: ${data.error}</p>`;
                }
            } else {
                resultDiv.innerHTML = `<p>Error: Unable to generate test. Please try again.</p>`;
            }
        } catch (error) {
            console.error("Error:", error);
            resultDiv.innerHTML = `<p>An unexpected error occurred.</p>`;
        } finally {
            loadingIndicator.style.display = "none"; // Hide the loading indicator
        }
    });
});
