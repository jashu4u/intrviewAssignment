#!/use/bin/perl
#######################################################################
#
# Purpose:  Common Module for logger and to get properties from xml
#
# Modification History:
#
# Date         Programmer      Version
# 07/22/2019   Jaswanth Koya   1.0
#
#######################################################################

package commonUtils;

#Initilize environment
our ($BASE);
BEGIN
{
	$BASE = "/projectName/bin";
}
use strict;
use warnings;
use Date::Manip;
use XML::Simple;
use MongoDB;
use JSON qw(to_json decode_json encode_json);
use POSIX qw(strftime);

#Global Variables
our $configProperties;

our @EXPORT_OK = qw($configProperties readXmlConfig mongoDbConn disconnMongoDb logToMongo returnOutput getTimeStamp logEvent);


# Reading config xml file
$configProperties = &readXmlConfig('$BASE/../config/CONFIGFILE.xml');

###################################################
# A function to connect to given mongoDb
###################################################
sub mongoDbConn {

	my $dbName = shift;
	#Here host and port is read from config xml.
	my $client = MongoDB::MongoClient->new( host => $configProperties->{dataBaseHost}, port => $configProperties->{dbPort} );
	my $database = $client->get_database($dbName);
	
	return $database;

}

###################################################
# A function to disconnect to given mongoDb
###################################################
sub disconnMongoDb {
	my ($database) = @_;
	$database->drop;
}

###################################################
# A function to log to given mongoDb connection
###################################################
sub logToMongo {
	my ($db, $collectionName, $logHash) = @_;
	my $collection = $db->get_collection("$collectionName");
	$collection->insert_one($logHash);
}

###################################################
# A function to read the XML configuration mail.
# Return value will be a hash which contains entire 
#		xml data
###################################################
sub readXmlConfig {
    my ( $fileName ) = @_;
    my $configParams = XMLin($fileName);

    return $configParams;
}

###################################################
# A function to get time and date
###################################################
sub getTimeStamp {
    my $format = shift;

	$format = '%Y-%m-%d' unless($format);
	my $timeStamp = strftime "$format", localtime;

    return $timeStamp;
}

###################################################
# A function to return json output for endpoints
###################################################
sub returnOutput {
	my ($fh, $scriptName, $message, $status) = @_;
	logToMongo($fh, $scriptName, "$message");
	logToMongo($fh, $scriptName, "Api execution ends.");
	close($fh);
	print $query->header( -type => 'application/json', -Pragma => 'no-cache' );
	print to_json({'returnCode' => $status, 'message' => "$message"});
	exit;
}


# A Function to log the events in the error log or the
# standard log file sent as an Open file handle to the
# function
#########################################################
sub logEvent {
    my ($Fh, $scriptName, $Data) = @_;

        $scriptName = basename($scriptName);
    print $Fh getTimeStamp("%m/%d/%Y %H:%M:%S")." $scriptName $Data\n";

    return 1;
}


########################################################
# To execute ibx wapis
########################################################
sub ibxRequest {

    my ($_objType
       ,$_params
       ,$_body)  = (@_);

    $_body       = ($_body ? to_json($_body) : '{}');

    our $ibx_user = $configProperties->{ibxUser};
    our $ibx_passwd = $configProperties->{ibxUser};
    our $ibx_url = $configProperties->{ibxUrl};

    my $results;
    my $status;


    if( ! $client ) {

        $client      = REST::Client->new({timeout => 3600});
        $client->setHost($ibx_url);
        $client->getUseragent()->ssl_opts(verify_hostname => 0);
        $client->getUseragent()->ssl_opts(SSL_verify_mode => 'SSL_VERIFY_NONE');

    }

    my $url2    = '/' . $_objType . $client->buildQuery($_params);
    my $headers = {Authorization => 'Basic '.  encode_base64($ibx_user . ':' . $ibx_passwd),};
    if( lc($_params->{_method}) eq 'delete' ) {
#
# DELETE
#
        $client->DELETE($url2, $headers);

        my $content      = $client->responseContent();
        $status          = ($client->responseCode() == 200  ? 1 : 0);

        if( $status ) {

            $results         = {_ref => $content};

        } else {

            $results         = from_json($content);

        }

    } elsif( lc($_params->{_method}) eq 'get' ) {
#
# GET
#
        $client->GET($url2 , $headers);
        my $content_json = $client->responseContent();

        eval {
             from_json($content_json);
             1;
        } or do {
             return 0, [{'Error' => $content_json}];
        };

        my $content      = from_json($content_json);
        $status          = ($content =~ /HASH.*/ && defined($content->{'Error'}) ? 0 : 1);
        $results         = ($content =~ /ARRAY.*/ ? $content : [$content]);


    } elsif( lc($_params->{_method}) eq 'post' ) {
#
# POST
#
        $client->POST($url2, $_body, $headers);
        my $content_json = $client->responseContent();
        $status          = ($client->responseCode() >= 200 && $client->responseCode() <= 299  ? 1 : 0);
        $results         = from_json($content_json);

    } elsif( lc($_params->{_method}) eq 'put' ) {
#
# PUT
#
        $client->POST($url2, $_body, $headers);

        my $content_json = $client->responseContent();
        $status          = ($client->responseCode() >= 200 && $client->responseCode() <= 299  ? 1 : 0);
        $results         = from_json($content_json);

    }
    return $status, $results;

}

1;
