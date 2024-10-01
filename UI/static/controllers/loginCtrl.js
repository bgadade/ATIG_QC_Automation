angular.module("myapp")
.controller("LoginController", function($scope,$state,authService,$window) {
    $scope.domain = ["EOC", "EC"];

    $scope.signIn=function(){
      $scope.selectedIndex = 0;
    }
    $scope.success="true";
    if ($window.localStorage['member-user'] == undefined) {
    }
    else{
      if (JSON.parse(window.localStorage['member-user'])["role"] == "admin") {
        $state.go("mngUsr");
      }
      else if(JSON.parse(window.localStorage['member-user'])["role"] == "user" ){
        $state.go("login");
      }
    }
    $scope.login = function() {
      $scope.error = "";
        authService.signIn($scope.user).then(function(user) {
          if(user.role=="admin"){
            $state.go("mngUsr");
          }
          else if(user.role=="user" && user.selectedDomain=="ER-Enrollment Receipt"){
            $state.go("home");
          }
          else if(user.role=="user" && user.selectedDomain=="EOC-Evidence Of Coverage"){
            $state.go("uploadExcel");
          }
          else
          {
            $scope.error="Invalid Credentials";
          }
        }, function(err) {
          console.log("error:",err);
          $scope.error = err.error;
        });

    }
});
