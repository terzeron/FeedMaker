TESTCASES= feed_maker_util.t remove_duplicates.t upload.t test.py ../../fma/test/test.py
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do echo "##### "$$testcase" #####"; env LC_ALL=C LANG=C ./$$testcase; done
