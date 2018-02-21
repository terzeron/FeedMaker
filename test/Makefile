TESTCASES= feedmakerutil.t remove_duplicates.t upload.t post_process_only_for_images.t test.py ../../fma/test/test.py
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do ./$$testcase; done
