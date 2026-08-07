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
    const { attachments, schools, requestId } = event.data || {};
    const findings = buildFindings(
      Array.isArray(attachments) ? attachments : [],
      Array.isArray(schools) ? schools : [],
    );
    self.postMessage({ requestId, findings });
  } catch (error) {
    self.postMessage({
      requestId: event.data && event.data.requestId,
      error: error instanceof Error ? error.message : String(error),
    });
  }
};
