// Use the same rendered page for the risk label and preview navigation.
export function resolveRiskPreviewPage(risk, index, pageMap = {}, pageCount = 0) {
  const positivePage = value => {
    const page = Number(value);
    return Number.isInteger(page) && page > 0 ? page : 0;
  };
  const page = positivePage(pageMap?.[String(index)]) || positivePage(risk?.page) || 1;
  const limit = positivePage(pageCount);
  return limit ? Math.min(page, limit) : page;
}
