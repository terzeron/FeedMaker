TESTCASES= extract.t feed_maker_util.t crawler1.t crawler2.t remove_duplicates.t upload.t test.py ../../fma/test/test.py
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do echo "##### "$$testcase" #####"; env LC_ALL=C LANG=C ./$$testcase; done
