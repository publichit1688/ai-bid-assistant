export function applyPreviewTextHighlight(container, risk, pageNumber, riskPage) {
    if (!container) return;
    const classes = ['highlight-high', 'highlight-middle', 'highlight-low'];
    container.querySelectorAll('.highlight-high,.highlight-middle,.highlight-low')
        .forEach((element) => element.classList.remove(...classes));
    if (!risk || Number(riskPage ?? risk.page) !== pageNumber) return;
    const words = Array.isArray(risk.highlight_words)
        ? risk.highlight_words.filter((word) => typeof word === 'string' && word.trim())
        : [];
    const level = String(risk.level || '');
    const className = level.includes('高') ? classes[0] : level.includes('中') ? classes[1] : classes[2];
    container.querySelectorAll('.react-pdf__Page__textContent span').forEach((span) => {
        const text = span.textContent || '';
        if (words.some((word) => text.includes(word))) span.classList.add(className);
    });
}
