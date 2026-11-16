document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('mm:toast', (e) => {
        const { message, level } = e.detail;
        console.log(`Toast [${level}]: ${message}`);
        alert(message);
    });
});
