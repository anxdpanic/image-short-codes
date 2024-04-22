insert = 'INSERT INTO shortcodes (shortcode,url) VALUES (?1,?2)'
select = 'SELECT shortcode, url FROM shortcodes WHERE shortcode = ?1'
delete = 'DELETE FROM shortcodes WHERE shortcode = ?1'
update = 'UPDATE shortcodes SET url = ?2 WHERE shortcode = ?1'
