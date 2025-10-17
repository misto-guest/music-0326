* pm2 need to improve with proper detection when automation faield and stopped. See also fixme in src/menu.py about handle_command function always returns True.


* EMPTY or Wrong list in iso-clipboard causes full automation fail. Different phones must be started with different commands. Think what to do better: wrong list  - jsut skip?

* On practice: if automation start failed - try close all application and  then start. add flag to applicaiton "close-all" to close all apps on phone before run command. 






















be  | 2025-10-17 09:43:52,842 - src.controllers.app_controllers.tidal_music - INFO - Tidal: IsoClipboard successfully brought to foreground
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:43:58,727 - src.controllers.app_controllers.tidal_music - INFO - Clicked FETCH Tidal button using XPath
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:12,058 - src.controllers.app_controllers.tidal_music - INFO - Looking for Tidal shuffle button...
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:14,053 - src.controllers.app_controllers.tidal_music - INFO - Clicked Tidal shuffle button
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:19,057 - src.controllers.app_controllers.tidal_music - INFO - Searching for mini_player element...
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:21,082 - src.controllers.app_controllers.tidal_music - INFO - Clicked mini_player to ensure correct Tidal state
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:25,639 - src.controllers.app_controllers.tidal_music - INFO - Minimizing Tidal window
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:28,371 - src.automation.multi_app_scheduler - INFO - Tidal Music initial setup completed
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:28,372 - src.automation.multi_app_scheduler - INFO - Starting Beatport initial setup...
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:28,373 - src.controllers.app_controllers.beatport_music - WARNING - Daily limit reached: 4.03 / 4h (Date: 2025-10-17)
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:28,376 - src.automation.multi_app_scheduler - WARNING - Beatport daily limit already reached, skipping setup
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:28,377 - src.cli.menu - ERROR - Failed to start music apps automation
9|#13-R5CR60LS9JX-sall_--exclude_amazon_youtube  | 2025-10-17 09:44:28,377 - src.cli.menu - ERROR - Failed to execute: Start All Apps
