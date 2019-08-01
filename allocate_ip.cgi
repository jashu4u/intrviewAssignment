#!/nslcm/system/bin/perl
#######################################################################
#
# Purpose:  To automate allocation of ipaddress to an ip in infoblox
#
# Modification History:
#
# Date         Programmer      Version
# 07/22/2019   Jaswanth Koya   1.0
#
#######################################################################

use strict;
use warnings;
use CGI;
use Getopt::Std;
use Net::DNS;
use Data::Dumper;
use commonUtils;
use JSON qw(to_json decode_json encode_json);

my $query = CGI->new();
my $inputParams = {};

my $collectionName = "$configProperties->{logCollection}";
#
# Get Db Connection
#
our $dbConn = mongoDbConn("$configProperties->{logDbName}");
logToMongo($dbConn, $collectionName, {$0 => { '_dateTime' => getTimeStamp(), 'log' => 'Api execution started' });
#
# Read parameters
#
&getParams();
#
# Process parameters
#
my @status = processParameters(%parameters);
returnOutput($dbConn, $collectionName, $query, $status[1], $status[0]) if( $status[0] != 200 );

@status = processHostName($hostName, $ip);
returnOutput($dbConn, $collectionName, $query, $status[1], $status[0]);


sub processParameters {
#
# Basic checking of passed parameters
#
    return(300,"[ERROR]: The fqdn parameter can not be blank") if ($inputParams->{fqdn} && $inputParams->{fqdn} eq "");
    return(300,"[ERROR]: The ipaddress parameter can not be blank") if ($inputParams->{ipaddress} && $inputParams->{ipaddress} eq "");

	$inputParams->{view} = 'Internal' unless($inputParams->{view} || $inputParams->{view} eq 'Internal' || $inputParams->{view} eq 'External' || $inputParams->{view} eq '');
#
# Validate host name
#
    return(300,"$inputParams->{fqdn} is not a valid fqdn") if( ! isValidHostNode($inputParams->{fqdn}) );

#
# Get subnet for IP Address from IPAM
#
    my($status
      ,$ipv4Object)     = getIpv4Addr($inputParams->{ipaddress}
                                     ,$inputParams->{view});

    return(300,"Error getting IP Address $inputParams->{ipaddress} from IPAM - $ipv4Object") if( ! $status );

    $inputParams->{ipv4Obj}    = $ipv4Object;
	
	logToMongo($dbConn, $collectionName, {$0 => { '_dateTime' => getTimeStamp(), 'log' => '[Info]: Parameters successfully processed' });
    return(200, "Parameters successfully processed");

}


sub processHostName {

    my ($hostName, $ip) = (@_);

    my @status     = getAvailableIpAddress();
    return(@status) if( $status[0] != 0 );

    @status       = updateIpam($ip,$hostName, $inputParams->{view});
    return(@status);

}


sub getAvailableIpAddress {

    my $ipv4Object = $params{ipv4Obj};

    my $objStat    = getObjectStatus($ipv4Object);
    return(300,"[ERROR]: Error $objStat", []) if( $objStat != 200);
#
# Is IP Address configured on an f5 device?
#
    my $f5Device = f5IpCheck($params{ti}); #this is a fucntion which will call f5 api to test whether ip is allocated or not.
    return(300,"[ERROR]: Error IP Address ($inputParams->{ipaddress}) found on f5 device ($f5Device)", []) if( $f5Device );

}

sub getObjectStatus {

    my ($ipv4Object)        = (@_);
#
# Is requested IP "Unused" in IPAM?
#
    foreach my $rec (@{$ipv4Object}) {

        return(300, "IP Address $params{ti} already in use") if(defined($rec->{status}) && $rec->{status} eq 'USED' && !(grep(/FA/, @{$rec->{types}}) || grep(/LEASE/, @{$rec->{types}}) || grep(/DHCP/, @{$rec->{usage}})) );

    }
    return('');

}

sub updateIpam {

    my($ip, $fqdn, $netView) = (@_);
#
# Add host to IPAM
#

    my ($status
       ,$message) = addIpamHostIpv4Addr($fqdn
                                       ,$ip
                                       ,$netView);
    return (300,"[ERROR]: There was an unhandled error trying to add IP $ip to IPAM " . Dumper($message)) if( $status );

    return (200, "[Info]: Assigned $ip to $fqdn");

}

# this fucntion to allocate ipaddress to teh given fqdn
sub addIpamHostIpv4Addr {

    my($_fqdn
      ,$_ipv4Addr
      ,$_dnsView)          = (@_);

	my $object_type        = 'record:host';
    
    my $body               = {name             => $_fqdn 
                             ,ipv4addrs        => [{ipv4addr => $_ipv4Addr}]
							 ,'view'   		   => $_dnsView
                             ,'network_view'   => 'default'};

    my $params             = {'_method'        => 'POST'
                             ,'_return_type'   => 'json'
                             ,'_return_fields' => 'name'};
    
    my ($status
       ,$response)  = ibxRequest($object_type, $params, $body);
    
    return (300, "[ERROR]: post $object_type failed - $response->{Error}") if( ! $status );

    $response->{ipv4Addr} = $_ipv4Addr;

    return (200, $response);

}

################################################################################################
#
# To validate fqdn
#
#################################################################################################
sub isValidHostNode($) {

    my ($node) = (@_);

    return 0 if(lc($node) eq 'null');
    return ($node =~ /^[A-Za-z0-9]{1}[A-Za-z0-9\-]{0,61}[A-Za-z0-9]{1}$/ ? 1 : 0);

}
################################################################################################
#
# grab query parameter
#
#################################################################################################
sub getParams {
    my $columnName;

    my @array = $query->param;
    for $columnName (@array) {
        $inputParams->{$columnName} = $query->param($columnName);
        $inputParams->{$columnName} =~ s/'/''/g;
    }
	
	if(exists $inputParams->{"POSTDATA"}){
		my $data = decode_json($inputParams->{POSTDATA});
		map {
				if(exists $data->{$_}) {
					$data->{$_} =~ s/\\/\\\\/g;
					$inputParams->{$_} = $data->{$_};
				}
			} ('fqdn','ipaddress','view');
	}
	logToMongo($dbConn, $collectionName, {$0 => { '_dateTime' => getTimeStamp(), 'log' => '[Info]: Input Params ' . Dumper($inputParams) });
}

