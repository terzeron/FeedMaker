TESTCASES= feedmakerutil.t remove_duplicate_line.t upload.t post_process_only_for_images.t
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do ./$$testcase; done
