Test cycle
<QA-T1126>1. install nightly build using ansible (shell)
	  2. check install version (shell)
	  
[done] <QA-T1127>3. check if system in prod mode (visual)
	  4. check monitors on (visual)
	  
[John] <QA-T1128>5. bootcheck3.0 (shell / 3 separate PCs)

[done] <QA-T1132>6. Assistant GUI shows await login (visual)

[done] <QA-T1129>7. Cart GUI show login screen (visual)

[done] <QA-T1133>8. Surgeon GUI show await login (visual)

[done] <QA-T1130>9. login Cart GUI with user / horizon (GUI Input)
	  10. check other screens show grayed-out after login success (visual)
	  
[done?]<QA-T1131>11. Cart GUI click ‘case setup’, enter random string for case ID, select OS or OD, select any surgeon from drop down list. (GUI Input)
	  12. verify ‘Move to draping’ button enabled. (visual) 
	  13. click ‘Move to draping’ (GUI Input)
	  14. check sim in Rviz on Tech PC, check Assistant GUI shows ‘Initialize Case button’, Cart GUI shows ‘System is ready for Draping’ (visual)
	  15. Assistant GUI click ‘Initialize case’ (GUI Input)
	  16. Assistant GUI check ‘ready for surgery, waiting for surgeon to start’ (visual)
	  17. Surgeon GUI check ‘start surgery’ button pops up (visual)
  	  18. Surgeon GUI click ‘start surgery’ (GUI Input)
	  19. Surgeon GUI ‘Apply docking to operative eye’ shows (visual)
	  20. Surgeon GUI click ‘confirm’ (GUI Input)
	  21. Surgeon GUI transitions into enabled screen (visual)
	  22. verify screens show properly (visual)
	  
[    ] <QA-T1139>23. check if surgical timer starts from 0, wait 5 min and check if timers are consistent within 5s (GUI)

[    ] <QA-T1134>24. check OCT shows on surgeon GUI and Assistant GUI and 3D TV (visual) <Take a screenshot>

[    ] <QA-T1135>25. OCT show color overlay, image is live (visual) <HARD with Squish>

[    ] <QA-T1138>26. check side camera on surgeon GUI (visual) <check today>

[    ] <QA-T1137>27. check wide camera on surgeon GUI (visual) <check today>

[    ] <QA-T1136>28. check Telecentric camera on assistant GUI (visual) <check today>

[    ] <QA-T1141>29. color overlay on Telecentric view is visible(visual) <HARD with Squish>

[    ] <QA-T1112>30. check data_recorder process for Cart / Cockpit running, and check Perception not running (shell)



Test Chains to automate
[    ] <QA-T1156>
[    ] <QA-T1158>
[    ] <QA-T1159>


grab handles for wide/side views OCT view
