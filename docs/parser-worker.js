self.window = self;
self.document = { addEventListener() {} };
self.localStorage = {
  getItem() { return null; },
  setItem() {},
  removeItem() {},
};
self.requestAnimationFrame = (callback) => callback();

importScripts("app/app.js");

self.onmessage = (event) => {
  try {
    const { attachments, schools, boundarySchools, requestId } = event.data || {};
    const analysis = analyzeBoardData(
      Array.isArray(attachments) ? attachments : [],
      Array.isArray(schools) ? schools : [],
      Array.isArray(boundarySchools) ? boundarySchools : schools,
    );
    self.postMessage({
      requestId,
      findings: analysis.findings,
      reviewCandidates: analysis.reviewCandidates,
    });
  } catch (error) {
    self.postMessage({
      requestId: event.data && event.data.requestId,
      error: error instanceof Error ? error.message : String(error),
    });
  }
};
