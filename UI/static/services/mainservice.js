angular.module("myapp")
.factory('mainService',function($http){
  var headers = {};
  function initialize(){
    headers = {};

}
    return{

     getConvertedFiles :function(uploadedFiles,callback){
     fileList = JSON.stringify(uploadedFiles);
      return $http.post('/convertPDF/'+fileList).then(function(response){

        callback(response);
        console.log("response",response);
      }).catch(function(response){
        console.log('Error:',response.status,response.data);
        callback(response);
      });


      },
     getPdfFile :function(filename,callback){
     fileName = JSON.stringify(filename);
      return $http.get('/getPdfFile/'+fileName, {responseType: 'arraybuffer'}).then(function(response){
        callback(response);
        console.log("response",response);
      }).catch(function(response){
        console.log('Error:',response.status,response.data);
        callback(response);
      });
    },
    setOutputData :function(outputData,callback){
    var output = {
      outputData: outputData,
      token: headers['token']
    };
    return $http.post('/getExcelFile/',output).then(function(response){
      callback(response);
    }).catch(function(response) {
      console.log('Error:', response.status, response.data);
      callback(response);
    });
  },
      ValidatePDFFiles :function(uploadedFiles,callback){
      fileList = JSON.stringify(uploadedFiles);
       return $http.post('/validatePDF/'+fileList).then(function(response){
         callback(response);
         console.log("response",response);
       }).catch(function(response){
         console.log('Error:',response.status,response.data);
         callback(response);
       });
     },
     getPDFResults : function(callback){
      return $http.post('/result/').then(function(response){
         callback(response);
         console.log("response",response);
       }).catch(function(response){
         console.log('Error:',response.status,response.data);
         callback(response);
       });
     },

     processPdfFiles : function(uploadedFiles,callback){
       console.log(uploadedFiles)
       token = headers['token']
       var dict = [];
       dict.push(uploadedFiles);
       dict.push(token);
      fileList = JSON.stringify(dict);
       return $http.get('/validatePDF/'+fileList).then(function(response){
         callback(response);
         console.log("response",response);
       }).catch(function(response){
         console.log('Error:',response.status,response.data);
         callback(response);
       });
     },
      saveFile :function(uploadedFiles,callback){
          headers['token'] = uploadedFiles['token']
          console.log(headers['token']);
      fileList = JSON.stringify(uploadedFiles);
       return $http.post('/saveInputFile/'+fileList).then(function(response){
         callback(response);
         console.log("response",response);
       }).catch(function(response){
         console.log('Error:',response.status,response.data);
         callback(response);
          });

       },
    getOutputdata :function(outputData,callback){
    outputData1 = JSON.stringify(outputData);
     return $http.post('/getOutputdata/'+outputData1).then(function(response){
        console.log("response",response);
        callback(response);

      }).catch(function(response){
        console.log('Error:',response.status,response.data);
        callback(response);
      });
    },
    getJSON :function(filename,callback){
      var obj = {
        filename: filename
      }
      return $http.post('/getJSON/',obj).then(function(response){
          callback(response);
      }).catch(function(response) {
        console.log('Error:', response.status, response.data);
        callback(response);
      });
    },
    addNewUser :function(userList,callback){
      return $http.post('/addNewUser/',userList).then(function(response){
        callback(response);
      }).catch(function(response) {
        console.log('Error:', response.status, response.data);
        callback(response);
      });
    },
    setDataList :function(dataList,filename,callback){
      var obj = {
        data : dataList,
        filename : filename,
      }
      return $http.post('/setJSON/',obj).then(function(response){
        callback(response);
      }).catch(function(response) {
        console.log('Error:', response.status, response.data);
        callback(response);
        });
      },
      }
});
