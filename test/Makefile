TESTCASES= feedmakerutil.t FeedMaker.t collection.t extraction.t
.PHONY: test

test: $(TESTCASES)
	@for testcase in $(TESTCASES); do ./$$testcase; done
