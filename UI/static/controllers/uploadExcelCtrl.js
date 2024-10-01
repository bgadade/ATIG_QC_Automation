angular.module("myapp")
.controller("uploadExcelController", function($location,$scope,Upload,fileUpload,mainService,authService,$rootScope,$state) {
  // mainService.initialize(); //to initialize all global variables
    $scope.user=authService.getUser();
    $scope.userName=authService.getUser().name;
    $scope.files = [];
    $scope.checkFile = true;
    $scope.showLoader = false;
    $scope.uploadedFileAndToken = {};

    $scope.upload = function (file) {
    // $scope.processDiv = false;
      $scope.showLoader = true;
    $rootScope.fileUploaded = null;
     var fileUploaded = $scope.myFile;
     $scope.files = file;
     var uploadUrl = "/uploadFiles/Excel/";
     $scope.progressVisible = true

      var upload = Upload.upload({
          url: uploadUrl,
          data: {file: fileUploaded}
      }).progress(function(evt) {
        console.log('percent: ' + parseInt(100.0 * evt.loaded / evt.total));
        $scope.progressPercentage = parseInt(100.0 * evt.loaded / evt.total);
      }).success(function(data, status, headers, config) {
        // $scope.uploadedFile = data;
        // $rootScope.fileUploaded = data;
         if($scope.uploadedFileAndToken != ""){
            swal("Good job!", "Files Uploaded successfully", "success");
            }
        $scope.uploadedFileAndToken = data;
        console.log('uploaded succesfully...');
        $scope.checkFile = false;
        $scope.showLoader = false;

      }).error(function(err) {
        console.log(err.stack);
      });
   };
   $scope.next =function () {
     $scope.uploadedFileAndToken["selectedYear"] = $scope.selectedYear;
     $scope.showLoader = true;
     console.log($scope.uploadedFileAndToken);
     mainService.saveFile($scope.uploadedFileAndToken,function(response){
         if (response.status >= 200 && response.status <= 299){
           $state.go("uploadPDF");
            $scope.showLoader = false;
         }
         else {
           $state.go("error");
         }

      });
   }
})
.directive('fileModel', ['$parse', function ($parse) {
            return {
               restrict: 'A',
               link: function(scope, element, attrs) {
                  var model = $parse(attrs.fileModel);
                  var modelSetter = model.assign;

                  element.bind('change', function(){
                     scope.$apply(function(){
                        modelSetter(scope, element[0].files[0]);
                     });
                  });
               }
            };
}]);
