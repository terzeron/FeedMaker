function createSuccess(payload = {}) {
  return { status: 'success', ...payload };
}

function createFailure(message, payload = {}) {
  return { status: 'failure', message, ...payload };
}

function isActiveName(name) {
  return !String(name || '').startsWith('_');
}

function withIsActive(items = [], getName = (item) => item?.name) {
  return items.map((item) => ({
    ...item,
    is_active: isActiveName(getName(item))
  }));
}

function createGroupsResponse(groups = []) {
  return createSuccess({ groups: withIsActive(groups) });
}

function createFeedsResponse(feeds = []) {
  return createSuccess({ feeds: withIsActive(feeds) });
}

function createProblemsResponse(result) {
  return createSuccess({ result });
}

function createExecResultResponse(execResult) {
  return createSuccess({ exec_result: execResult });
}

function createSearchResponse(feeds = []) {
  return createSuccess({ feeds });
}

function createSearchSiteResponse(searchResult = '') {
  return createSuccess({ search_result: searchResult });
}

function createSiteNamesResponse(siteNames = []) {
  return createSuccess({ site_names: siteNames });
}

function createSiteConfigResponse(configuration = {}) {
  return createSuccess({ configuration });
}

function createFeedInfoResponse(feedInfo) {
  return createSuccess({ feed_info: feedInfo });
}

function createCheckRunningResponse(runningStatus) {
  return createSuccess({ running_status: Boolean(runningStatus) });
}

function createItemTitlesResponse(itemTitles = []) {
  return createSuccess({ item_titles: itemTitles });
}

function createNewNameResponse(newName) {
  return createSuccess({ new_name: newName });
}

module.exports = {
  createSuccess,
  createFailure,
  isActiveName,
  withIsActive,
  createGroupsResponse,
  createFeedsResponse,
  createProblemsResponse,
  createExecResultResponse,
  createSearchResponse,
  createSearchSiteResponse,
  createSiteNamesResponse,
  createSiteConfigResponse,
  createFeedInfoResponse,
  createCheckRunningResponse,
  createItemTitlesResponse,
  createNewNameResponse
};
