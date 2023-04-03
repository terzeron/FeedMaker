TESTCASES=test_notification.py test_feed_maker_util.py test_new_list_collector.py test_extractor.py test_headless_browser.py test_crawler1.py test_crawler2.py test_crawler3.py test_uploader.py test_feed_maker.py test_run.py test_some_scripts.py test_problem_manager.py ${FEED_MAKER_WORK_DIR}/test/test.py
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do echo "######## "$$testcase" ########"; env LC_ALL=C LANG=C python $$testcase; done
