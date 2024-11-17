INSERT INTO chaturbate (streamer_name, followers) 
		SELECT streamer_name,followers
        from cc.models
		WHERE streamer_name='aryamirelle'
        ON CONFLICT (streamer_name)
        DO UPDATE SET 
        followers=EXCLUDED.followers,
        viewers=EXCLUDED.viewers, 
        last_broadcast=DATETIME('now', 'localtime'),
        most_viewers=MAX(most_viewers, EXCLUDED.viewers) 
		