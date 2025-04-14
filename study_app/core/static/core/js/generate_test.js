document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("generateTestForm");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const resultDiv = document.getElementById("result");

    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Stop the page from refreshing

        loadingIndicator.style.display = "block"; // Show loading indicator

        const formData = new FormData(form); // Collect form data

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: formData,
                headers: {
                    "X-CSRFToken": document.querySelector('input[name="csrfmiddlewaretoken"]').value, // CSRF Token
                },
            });

            if (response.ok) {
                const data = await response.json(); // Parse JSON response
                if (data.success) {
                    // Show the generated test/questions
                    resultDiv.innerHTML = `<pre>${data.test}</pre>`;
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
            loadingIndicator.style.display = "none"; // Hide loading indicator
        }
    });
});