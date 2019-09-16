This assignment basically concentrated on one cgi program and logs to mongodb.
 1.commonUtils.pm:
      This perl module supports below listed subroutines
      readXmlConfig mongoDbConn disconnMongoDb logToMongo returnOutput getTimeStamp
      readXmlConfig: This function will read xml and return xml data in hash format. Basically this function will be used for property xml file reading.
      mongoDbConn: This function is used to connect to given mongodb database.
      disconnMongoDb : This function is used to disconnect from the given mongodb database
      logToMongo: This function is used to log content in given mongodb collection
      returnOutput: This function is used to return json output of cgi
      getTimeStamp: To get time stamp
      logEvent: To log into a file.

  2. allocate_ip.cgi: 
      This cgi code is used to allocate ipaddres to the given fqdn in infoblox. Basically this is an automation of manual infoblox ip allocation. This cgi uses logToMongo and returnOutput of commonUtils.pm
      
  3. config.xml: 
      This is propeties xml file of application.
    
