console.log("Eventora loaded successfully.");
// ========== HERO CAROUSEL ==========
document.addEventListener('DOMContentLoaded', function () {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.dot');
    let current = 0;

    if (slides.length === 0) return;

    function showSlide(index) {
        slides.forEach(s => s.classList.remove('active'));
        dots.forEach(d => d.classList.remove('active'));
        slides[index].classList.add('active');
        dots[index].classList.add('active');
        current = index;
    }

    dots.forEach(dot => {
        dot.addEventListener('click', function () {
            showSlide(parseInt(this.dataset.slideBtn));
        });
    });

    setInterval(function () {
        showSlide((current + 1) % slides.length);
    }, 5000);
});