TESTCASES= feedmakerutil.t remove_duplicates.t upload.t test.py ../../fma/test/test.py
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do ./$$testcase; done
