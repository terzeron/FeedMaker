rm -f TAGS
find . -name "*.p[lmy]" -exec etags --append "{}" \;
