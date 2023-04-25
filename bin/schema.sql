-- alias -> name
CREATE TABLE feed_alias_name
(
    feed_alias VARCHAR(256) NOT NULL,
    feed_name  VARCHAR(256) NOT NULL,
    PRIMARY KEY (feed_alias)
);
-- name --> list of aliases
CREATE INDEX feed_alias_name_map_feed_name_idx ON feed_alias_name (feed_name);

-- name -> title, group
CREATE TABLE feed_name_title_group
(
    feed_name  VARCHAR(256) NOT NULL,
    feed_title VARCHAR(256) NOT NULL,
    group_name VARCHAR(256) NOT NULL,
    PRIMARY KEY (feed_name)
);

-- name -> public_feed_info
CREATE TABLE feed_name_public_feed_info
(
    feed_name   VARCHAR(256) NOT NULL,
    feed_title  VARCHAR(256) NOT NULL,
    group_name  VARCHAR(256) NOT NULL,
    file_path   VARCHAR(512) NOT NULL,
    upload_date TIMESTAMP default null,
    file_size   INT           NOT NULL,
    num_items   INT           NOT NULL,
    PRIMARY KEY (feed_name)
);

-- name -> config
CREATE TABLE feed_name_config
(
    feed_name VARCHAR(256) NOT NULL,
    config    text          NOT NULL,
    PRIMARY KEY (feed_name)
);

-- name -> rss_info
CREATE TABLE feed_name_rss_info
(
    feed_name   VARCHAR(256) NOT NULL,
    update_date TIMESTAMP default null,
    PRIMARY KEY (feed_name)
);

-- alias -> progress_info
CREATE TABLE feed_name_progress_info
(
    feed_name      VARCHAR(256) NOT NULL,
    feed_title     VARCHAR(256) NOT NULL,
    group_name     VARCHAR(256) NOT NULL,
    idx            INT           NOT NULL,
    count          INT         NOT NULL,
    unit_size      float           NOT NULL,
    progress_ratio float         NOT NULL,
    due_date       TIMESTAMP default null,
    PRIMARY KEY (feed_name)
);

-- alias -> access_info
CREATE TABLE feed_alias_access_info
(
    feed_alias    VARCHAR(256) NOT NULL,
    feed_name     VARCHAR(256) NOT NULL,
    access_date   TIMESTAMP default null,
    access_status INT       default null,
    view_date     TIMESTAMP default null,
    view_status   INT       default null,
    is_in_xml_dir boolean       NOT NULL,
    PRIMARY KEY (feed_alias)
);

-- alias -> status_info
CREATE TABLE feed_alias_status_info
(
    feed_alias   VARCHAR(256) NOT NULL,
    feed_name    VARCHAR(256) NOT NULL,
    feed_title   VARCHAR(256),
    group_name   VARCHAR(256),
    htaccess     boolean       default false,
    http_request boolean       default false,
    public_html  boolean       default false,
    feedmaker    boolean       default false,
    access_date  TIMESTAMP     default null,
    view_date    TIMESTAMP     default null,
    upload_date  TIMESTAMP     default null,
    update_date  TIMESTAMP     default null,
    file_path    VARCHAR(512) default null,
    PRIMARY KEY (feed_alias)
);

-- html_file -> size
CREATE TABLE html_file_size
(
    file_path      VARCHAR(512) NOT NULL,
    file_name      VARCHAR(256) NOT NULL,
    feed_dir_path  VARCHAR(512) NOT NULL,
    group_dir_path VARCHAR(512) NOT NULL,
    size           INT           NOT NULL,
    update_date    TIMESTAMP default null,
    PRIMARY KEY (file_path)
);
CREATE INDEX html_file_size_feed_dir_path_idx ON html_file_size (feed_dir_path);
CREATE INDEX html_file_size_group_dir_path_idx ON html_file_size (group_dir_path);

-- html_file -> with_many_image_tag
CREATE TABLE html_file_with_many_image_tag
(
    file_path      VARCHAR(512) NOT NULL,
    file_name      VARCHAR(256) NOT NULL,
    feed_dir_path  VARCHAR(512) NOT NULL,
    group_dir_path VARCHAR(512) NOT NULL,
    count          INT           NOT NULL,
    PRIMARY KEY (file_path)
);
CREATE INDEX html_file_with_many_image_tag_feed_dir_path_idx ON html_file_with_many_image_tag (feed_dir_path);
CREATE INDEX html_file_with_many_image_tag_group_dir_path_idx ON html_file_with_many_image_tag (group_dir_path);

-- html_file -> without_image_tag
CREATE TABLE html_file_without_image_tag
(
    file_path      VARCHAR(512) NOT NULL,
    file_name      VARCHAR(256) NOT NULL,
    feed_dir_path  VARCHAR(512) NOT NULL,
    group_dir_path VARCHAR(512) NOT NULL,
    count          INT           NOT NULL,
    PRIMARY KEY (file_path)
);
CREATE INDEX html_file_without_image_tag_feed_dir_path_idx ON html_file_without_image_tag (feed_dir_path);
CREATE INDEX html_file_without_image_tag_group_dir_path_idx ON html_file_without_image_tag (group_dir_path);

-- html_file -> image_not_found
CREATE TABLE html_file_image_not_found
(
    file_path      VARCHAR(512) NOT NULL,
    file_name      VARCHAR(256) NOT NULL,
    feed_dir_path  VARCHAR(512) NOT NULL,
    group_dir_path VARCHAR(512) NOT NULL,
    count          INT           NOT NULL,
    PRIMARY KEY (file_path)
);
CREATE INDEX html_file_image_not_found_feed_dir_path_idx ON html_file_image_not_found (feed_dir_path);
CREATE INDEX html_file_image_not_found_group_dir_path_idx ON html_file_image_not_found (group_dir_path);

-- feed_name -> list_url_count
CREATE TABLE feed_name_list_url_count
(
    feed_name  VARCHAR(256) NOT NULL,
    feed_title VARCHAR(256) NOT NULL,
    group_name VARCHAR(256) NOT NULL,
    count      INT           NOT NULL,
    PRIMARY KEY (feed_name)
);

-- element_name -> count
CREATE TABLE element_name_count
(
    element_name VARCHAR(256) NOT NULL,
    count        INT          NOT NULL,
    PRIMARY KEY (element_name)
);

CREATE TABLE lock_for_concurrent_loading
(
    lock_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
