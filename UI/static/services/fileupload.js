angular.module("myapp")
.service('fileUpload', ['$http', function ($http) {
  this.uploadFileToUrl = function(file, uploadUrl){
    console.log("inside file upload service*********************");
    console.log(uploadUrl);
    var fd = new FormData();
    console.log(fd);
    fd.append('file', file);
    return $http.post(uploadUrl, fd, {
      transformRequest: angular.identity,
      headers: {'Content-Type': undefined},
      cache : false
    }).then(function(data){
      console.log(data);
      console.log("inside success");
    });
  }
}])
