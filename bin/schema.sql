-- alias -> name
create table feed_alias_name
(
    feed_alias varchar(256) not null,
    feed_name  varchar(256) not null,
    primary key (feed_alias)
);
-- name --> list of aliases
create index feed_alias_name_map_feed_name_idx on feed_alias_name (feed_name);

-- name -> title, group
create table feed_name_title_group
(
    feed_name  varchar(256) not null,
    feed_title varchar(256) not null,
    group_name varchar(256) not null,
    primary key (feed_name)
);

-- name -> public_feed_info
create table feed_name_public_feed_info
(
    feed_name   varchar(256) not null,
    feed_title  varchar(256) not null,
    group_name  varchar(256) not null,
    file_path   varchar(512) not null,
    upload_date timestamp default null,
    file_size   int           not null,
    num_items   int           not null,
    primary key (feed_name)
);

-- name -> config
create table feed_name_config
(
    feed_name varchar(256) not null,
    config    text          not null,
    primary key (feed_name)
);

-- name -> rss_info
create table feed_name_rss_info
(
    feed_name   varchar(256) not null,
    update_date timestamp default null,
    primary key (feed_name)
);

-- alias -> progress_info
create table feed_name_progress_info
(
    feed_name      varchar(256) not null,
    feed_title     varchar(256) not null,
    group_name     varchar(256) not null,
    idx            int           not null,
    count          int         not null,
    unit_size      float           not null,
    progress_ratio float         not null,
    due_date       timestamp default null,
    primary key (feed_name)
);

-- alias -> access_info
create table feed_alias_access_info
(
    feed_alias    varchar(256) not null,
    feed_name     varchar(256) not null,
    access_date   timestamp default null,
    access_status int       default null,
    view_date     timestamp default null,
    view_status   int       default null,
    is_in_xml_dir boolean       not null,
    primary key (feed_alias)
);

-- alias -> status_info
create table feed_alias_status_info
(
    feed_alias   varchar(256) not null,
    feed_name    varchar(256) not null,
    feed_title   varchar(256),
    group_name   varchar(256),
    htaccess     boolean       default false,
    http_request boolean       default false,
    public_html  boolean       default false,
    feedmaker    boolean       default false,
    access_date  timestamp     default null,
    view_date    timestamp     default null,
    upload_date  timestamp     default null,
    update_date  timestamp     default null,
    file_path    varchar(512) default null,
    primary key (feed_alias)
);

-- html_file -> size
create table html_file_size
(
    file_path      varchar(512) not null,
    file_name      varchar(256) not null,
    feed_dir_path  varchar(512) not null,
    group_dir_path varchar(512) not null,
    size           int           not null,
    update_date    timestamp default null,
    primary key (file_path)
);
create index html_file_size_feed_dir_path_idx on html_file_size (feed_dir_path);
create index html_file_size_group_dir_path_idx on html_file_size (group_dir_path);

-- html_file -> with_many_image_tag
create table html_file_with_many_image_tag
(
    file_path      varchar(512) not null,
    file_name      varchar(256) not null,
    feed_dir_path  varchar(512) not null,
    group_dir_path varchar(512) not null,
    count          int           not null,
    primary key (file_path)
);
create index html_file_with_many_image_tag_feed_dir_path_idx on html_file_with_many_image_tag (feed_dir_path);
create index html_file_with_many_image_tag_group_dir_path_idx on html_file_with_many_image_tag (group_dir_path);

-- html_file -> without_image_tag
create table html_file_without_image_tag
(
    file_path      varchar(512) not null,
    file_name      varchar(256) not null,
    feed_dir_path  varchar(512) not null,
    group_dir_path varchar(512) not null,
    count          int           not null,
    primary key (file_path)
);
create index html_file_without_image_tag_feed_dir_path_idx on html_file_without_image_tag (feed_dir_path);
create index html_file_without_image_tag_group_dir_path_idx on html_file_without_image_tag (group_dir_path);

-- html_file -> image_not_found
create table html_file_image_not_found
(
    file_path      varchar(512) not null,
    file_name      varchar(256) not null,
    feed_dir_path  varchar(512) not null,
    group_dir_path varchar(512) not null,
    count          int           not null,
    primary key (file_path)
);
create index html_file_image_not_found_feed_dir_path_idx on html_file_image_not_found (feed_dir_path);
create index html_file_image_not_found_group_dir_path_idx on html_file_image_not_found (group_dir_path);

-- feed_name -> list_url_count
create table feed_name_list_url_count
(
    feed_name  varchar(256) not null,
    feed_title varchar(256) not null,
    group_name varchar(256) not null,
    count      int           not null,
    primary key (feed_name)
);

-- element_name -> count
create table element_name_count
(
    element_name varchar(256) not null,
    count        int          not null,
    primary key (element_name)
);