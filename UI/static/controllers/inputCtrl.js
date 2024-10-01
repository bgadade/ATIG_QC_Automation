angular.module("myapp")
.directive('fileModel', ['$parse', function ($parse) {
            return {
               restrict: 'A',
               link: function(scope, element, attrs) {
//                  var model = $parse(attrs.fileModel);
//                  var modelSetter = model.assign;

                  element.bind('change', function(){
                   $parse(attrs.fileModel).assign(scope,element[0].files)
                     scope.$apply();
                  });
               }
            };
}])

.controller("InputController", function($scope,Upload,fileUpload,$rootScope,mainService,$window,$sce) {
    $scope.data = [];
    $scope.pageReload = function(){
    location.reload(true);
    }
    $scope.show = false;
    $scope.showLoader = false;
    $scope.disableRun = true;
    $scope.showConvertedFiles = false;
    $scope.uploadedFiles123 = ['a cd','bew','sdfs'];
    $scope.fileStatus = [];
    $scope.outputGnrtd = [];
    $scope.pdfData = [];

    $scope.upload = function (file) {
    $scope.showLoader = true;
    $rootScope.fileUploaded = null;
    $scope.browseButton = false;
    var fileUploaded = [];
    fileUploaded.push($scope.myFile)
//    fileUploaded = $scope.myFile;
     $scope.files = file;
     var uploadUrl = "/uploadFiles/upload/";
//    $scope.showLoader = true;

      var upload = Upload.upload({

          url: uploadUrl,
          data: {file: fileUploaded}
      }).progress(function(evt) {
        // console.log('percent: ' + parseInt(100.0 * evt.loaded / evt.total));
        $scope.progressPercentage = parseInt(100.0 * evt.loaded / evt.total);
      }).success(function(data, status, headers, config) {
            $scope.browseButton = true;
            $scope.showLoader = false;
            $rootScope.fileUploaded = data;
            $scope.uploadedFiles = data.filenames;
            if($scope.uploadedFiles != ""){
            swal("Good job!", "Files Uploaded successfully", "success");
            }
             $scope.disableRun = false;
            console.log(data);
            console.log('uploaded succesfully...');


      }).error(function(err) {
        console.log(err.stack);
      });


   };
            //converPDF

       $scope.getConvertedFiles = function(){
//        $scope.disableRun = true;
        $scope.browseButton = true;
        $scope.showLoader = true;
        mainService.getConvertedFiles($rootScope.fileUploaded,function(response){
         console.log(response);
         $scope.fileStatus = response.data.data;
          console.log($scope.fileStatus);
          $scope.showConvertedFiles =true;
          $scope.showLoader = false;
          $scope.disableRun = true;
       });
       console.log("filestatus",$scope.fileStatus);
       }
//    $scope.gnrtOtpt=true;

      $scope.ValidatePDF = function(){
        mainService.ValidatePDFFiles($rootScope.fileUploaded,function(response){
        console.log(response)  ;
        });
      }

    $scope.getOutputdata = function(e){
    console.log("filestatus 1",$scope.fileStatus);
     e.preventDefault();
    mainService.getOutputdata($scope.fileStatus,function(response){
       $scope.outputGnrtd = response.data;
       console.log($scope.outputGnrtd);
       var ws = XLSX.utils.json_to_sheet($scope.outputGnrtd, {header:['SNo','file_name', 'Component Code', 'Comments', 'Pass_Fail']});
       var wb = XLSX.utils.book_new();
       XLSX.utils.book_append_sheet(wb, ws);
       XLSX.writeFile(wb, "outputFile.xlsx");
       console.log(response)
    });
    }
    $scope.processPdfFiles = function () {
    $scope.showLoader = true;
      console.log($rootScope.fileUploaded)
      mainService.processPdfFiles($rootScope.fileUploaded,function(response){
        if (response.status >= 200 && response.status <= 299){
          $scope.showLoader = false;
          $scope.showConvertedFiles = true;
          console.log(response);
          $scope.pdfData = response.data;
          console.log($scope.pdfData);
        }
      });
    }
     $scope.c = 0;
     $scope.getPDF = function(fileName,status){
       $scope.c++;
       if(status=="Fail"){
         mainService.getPdfFile(fileName,function(response){
           if(response.status>=200 && response.status<=299){
             console.log(response);
             console.log($scope.c);
             var file = new Blob([response.data], {type: 'application/pdf'});
             var fileURL = URL.createObjectURL(file);
              $window.open(fileURL,'C-Sharpcorner'+$scope.c,'width=700,height=600');
           }

         });
       }
     }
    $scope.outFile = null;
    $scope.setOutputData = function(e){
      e.preventDefault();
      var btn_href = $('#dwnldFile').attr("href", "/static/output/").attr("href");
      mainService.setOutputData($scope.pdfData,function(response){
        if (response.status >= 200 && response.status <= 299){
          $scope.outputToken =response.data["token"]
          $scope.out_filename=response.data["filename"]+".xlsx";
          $scope.outFile = response.data["filename"]
          console.log($scope.outFile);
          // $location.path('/getDwnldfile/'+$scope.outFile);
         $('#dwnldFile').attr("href", btn_href + $scope.out_filename+"/");
          $("#dwnldFile")[0].click();
        }
        // else {
        //   $state.go("error");
        // }
      });
    }
//    $scope.openWindow = function(fileName,status) {
//      if(status=="Fail"){
//        $scope.url = 'static/input/'+fileName;
//       $window.open($scope.url, 'C-Sharpcorner', 'width=700,height=600');
//      }
//      else{
//          $scope.url="";
//      }
//     }
   });
