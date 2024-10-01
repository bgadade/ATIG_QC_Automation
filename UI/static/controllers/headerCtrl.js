angular.module("myapp")

.controller("HeaderController", function($scope,authService,$state,$rootScope) {
  $scope.state = $state;
  $scope.user=authService.getUser();
  if($scope.user != undefined || $scope.user != null){
    $scope.userName=authService.getUser().name;
    $scope.userRole=authService.getUser().role;
    $scope.domain=authService.getUser().selectedDomain;
  }
  else{
    $state.go("login");
  }

  $scope.logout = function(){
    authService.signout()
    .then(function(res){
      authService.removeUser();
      $state.go("login");
    },
    function(res){
      $state.go("login");
      // , {error: "Invalid signin attempt, please retry with valid credentials"});
    });
  }
  // $rootScope.footerDiv = false;
  $scope.hideFooter = function(){
    if ($rootScope.footerDiv) {
      $rootScope.footerDiv = false;
    }
    else{
      $rootScope.footerDiv = true;
    }
  }
});
