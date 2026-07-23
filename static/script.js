document.querySelectorAll(".jar-btn").forEach(button => {

    button.addEventListener("click", () => {

        document.querySelector("#jar_id").value = button.dataset.id;

        document.querySelector("#jar_name").textContent =
            button.dataset.name;

        document.querySelector("#overlay").classList.remove("hidden");

    });

});