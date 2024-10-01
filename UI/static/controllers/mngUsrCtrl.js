angular.module("myapp")

.controller("MngUsrController", function($scope,mainService,$state) {
    $scope.usersList = [];
    $scope.getUserList = function(){
      mainService.getJSON("credentials.json",function(response){
        if (response.status >= 200 && response.status <= 299)
        {
          $scope.usersList = response.data;
        }
        else {
          $state.go("error");
        }
      });
    }

    $scope.addNewUser = function(){
      console.log($scope.user);
      $scope.user.role = "user";
      mainService.addNewUser($scope.user,function(response) {
        if (response.status >= 200 && response.status <= 299)
        {
          $scope.user = {};
          $scope.confirmPassword=null;
          console.log("user saved successfully:",response);
          swal("Good job!", "user saved successfully", "success");
        }
        else{
          $state.go("error");
        }
      });
    };

    $scope.removeUser = function(index){
      $scope.usersList.splice(index,1);
    };

    $scope.setUsersList = function(){
      mainService.setDataList($scope.usersList,"credentials.json",function(response){
        if (response.status >= 200 && response.status <= 299) {
          console.log("Set Users:",response.data);
           swal("Good job!", "Users Updated Successfully", "success");
          $scope.getUserList();
        }
        else{
          $state.go("error");
        }
      });
    };

});
