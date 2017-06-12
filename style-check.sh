REPORTS_FOLDER=.style-reports
mkdir -p $REPORTS_FOLDER
flake8 --ignore=F403,F405 --max-line-length=120 --exclude $REPORTS_FOLDER/ --tee --output-file $REPORTS_FOLDER/report-$(date +"%m-%d-%Y-%T").txt snn_utils
exit $?
