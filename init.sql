use feedmaker;

DROP TABLE IF EXISTS group_info;
CREATE TABLE group_info
(
    group_name VARCHAR(256) NOT NULL,
    feed_name  VARCHAR(256) NOT NULL,
    PRIMARY KEY (group_name)
);

DROP TABLE IF EXISTS feed_info;
CREATE TABLE feed_info
(
    feed_name             VARCHAR(256) NOT NULL,
    feed_title            VARCHAR(256) DEFAULT NULL,
    group_name            VARCHAR(256) DEFAULT NULL,

    is_active             BOOLEAN      DEFAULT FALSE,
    config                TEXT         DEFAULT NULL,
    config_modify_date    TIMESTAMP    DEFAULT NULL,
    url_list_count        INT          DEFAULT NULL,

    collect_date          TIMESTAMP    DEFAULT NULL,

    is_completed          BOOLEAN      DEFAULT FALSE,
    current_index         INT          DEFAULT NULL,
    total_item_count      INT          DEFAULT NULL,
    unit_size_per_day     FLOAT        DEFAULT NULL,
    progress_ratio        FLOAT        DEFAULT NULL,
    due_date              TIMESTAMP    DEFAULT NULL,

    feedmaker             BOOLEAN      DEFAULT FALSE,
    rss_update_date       TIMESTAMP    DEFAULT NULL,

    public_html           BOOLEAN      DEFAULT FALSE,
    public_feed_file_path VARCHAR(512) DEFAULT NULL,
    file_size             INT          DEFAULT NULL,
    num_items             INT          DEFAULT NULL,
    upload_date           TIMESTAMP    DEFAULT NULL,

    http_request          BOOLEAN      DEFAULT FALSE,
    access_date           TIMESTAMP    DEFAULT NULL,
    view_date             TIMESTAMP    DEFAULT NULL,
    PRIMARY KEY (feed_name)
);
CREATE INDEX feed_info_access_date_idx ON feed_info (access_date);
CREATE INDEX feed_info_view_date_idx ON feed_info (view_date);

-- html_file -> size
DROP TABLE IF EXISTS html_file_info;
CREATE TABLE html_file_info
(
    file_path                  VARCHAR(512) NOT NULL,
    file_name                  VARCHAR(256) NOT NULL,
    feed_dir_path              VARCHAR(512) DEFAULT NULL,
    size                       INT          DEFAULT NULL,
    count_with_many_image_tag  INT          DEFAULT NULL,
    count_without_image_tag    INT          DEFAULT NULL,
    count_with_image_not_found INT          DEFAULT NULL,
    update_date                TIMESTAMP    DEFAULT NULL,
    PRIMARY KEY (file_path)
);
CREATE INDEX html_file_info_feed_dir_path_idx ON html_file_info (feed_dir_path);

-- element_name -> count
DROP TABLE IF EXISTS element_name_count;
CREATE TABLE element_name_count
(
    element_name VARCHAR(256) NOT NULL,
    count        INT          NOT NULL,
    PRIMARY KEY (element_name)
);

DROP TABLE IF EXISTS lock_for_concurrent_loading;
CREATE TABLE lock_for_concurrent_loading
(
    lock_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
