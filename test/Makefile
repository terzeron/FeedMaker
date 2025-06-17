# test_feed_maker_util_config.py \
# test_feed_maker_util_data.py \
# test_feed_maker_util_datetime.py \
# test_feed_maker_util_file_manager.py \
# test_feed_maker_util_html_extractor.py \
# test_feed_maker_util_io.py \
# test_feed_maker_util_path_util.py \
# test_feed_maker_util_process.py \
# test_feed_maker_util_url.py \
# test_headless_browser.py \
# test_crawler1.py \
# test_crawler2.py \
# test_crawler3.py \
# test_notification.py \
# test_uploader.py \
# test_extractor.py \
# test_download_image.py \
# test_download_merge_split.py
TESTCASES=\
test_db.py \
test_access_log_manager.py \
test_new_list_collector.py \
test_feed_maker.py \
test_feed_manager.py \
test_html_file_manager.py \
test_problem_manager.py \
test_run.py \
test_backend.py \
test_backend2.py \
${FM_WORK_DIR}/test/test.py

.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do echo "######## "$$testcase" ########"; env LC_ALL=C LANG=C python $$testcase || break; done && echo "completed successfully"
